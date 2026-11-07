//! WS2812 input receiver: the v2.3 frame from the host on LED_IN.
//!
//! Design: `docs/INPUT_CAPTURE_OPTIONS.md` option 4a, resource split B.
//! TIM3 runs in PWM-input mode on CH1 (PA6, ball F1): every rising edge
//! resets AND starts the counter (combined reset + trigger slave mode), the
//! falling edge captures the high time in CCR2, and each CC2 event makes
//! DMA1_CH2 copy CCR2's low byte into a circular 1024-byte ring. When no
//! rising edge comes for 20 us (ARR = 959 at 48 MHz) the counter overflows
//! and, in one-pulse mode, stops: one update interrupt per frame, none while
//! the line idles. The interrupt only snapshots the DMA write index and
//! signals the task (`hw.rs`); the task thresholds the 480 widths, packs 60
//! bytes and checks markers + CRC (`rbarf_proto`, host-tested).
//!
//! Why this shape: the CPU does nothing during the 600 us frame, nothing is
//! re-armed between frames, and each bit is timed from its own rising edge,
//! so the first bit after idle is measured like every other and HSI error
//! cannot accumulate (no sampling grid, no calibration).
//!
//! Ownership of [`crate::FRAME`]: the first valid frame sets
//! [`crate::DEMO_STOP`], after which only this task writes `FRAME`. A bad
//! frame is counted by cause and dropped; the previous frame stays shown.
//!
//! Logging: one `rx:` stats line per second, printed by the heartbeat via
//! [`log_stats`] (cumulative counters, per-second width ranges).

mod hw;

use core::cell::RefCell;
use core::sync::atomic::Ordering;

use defmt::info;
use embassy_stm32::dma;
use embassy_sync::blocking_mutex::Mutex;
use embassy_sync::blocking_mutex::raw::CriticalSectionRawMutex;
use rbarf_proto::{FRAME_BITS, Reject, Vote, WidthStats};

use crate::board::{self, RxPeripherals};

pub use hw::{RING_LEN, RING_MASK};

/// Receive counters. `ok`..`missed` are cumulative since boot; `widths` is
/// reset every second by [`log_stats`].
#[derive(Clone, Copy)]
struct Stats {
    ok: u32,
    short: u32,
    long: u32,
    marker: u32,
    crc: u32,
    /// CC2 overcapture flagged by the ISR (a width was lost).
    ovr: u32,
    /// The DMA overwrote the frame before the task finished reading it.
    late: u32,
    /// End-of-frame events the task never saw (the Signal kept only the newest).
    missed: u32,
    /// Accepted although the three CRC copies were not all equal.
    vote: u32,
    widths: WidthStats,
    /// First 4 data bytes of the last accepted frame (the bench soak puts the
    /// frame number there).
    last: u32,
}

static STATS: Mutex<CriticalSectionRawMutex, RefCell<Stats>> = Mutex::new(RefCell::new(Stats {
    ok: 0,
    short: 0,
    long: 0,
    marker: 0,
    crc: 0,
    ovr: 0,
    late: 0,
    missed: 0,
    vote: 0,
    widths: WidthStats::EMPTY,
    last: 0,
}));

#[cfg(feature = "rx-hist")]
static HIST: Mutex<CriticalSectionRawMutex, RefCell<[u32; 64]>> = Mutex::new(RefCell::new([0; 64]));

/// Brings up TIM3, the DMA ring and the pin, then receives forever.
#[embassy_executor::task]
pub async fn rx_task(p: RxPeripherals) {
    // The DMA channel and its circular Transfer live in this task's future
    // for the life of the program: the Transfer is never awaited (circular
    // never ends) and never dropped (dropping it would stop the DMA).
    let request = <board::RxDma as embassy_stm32::timer::Dma<board::RxTimer, embassy_stm32::timer::Ch2>>::request(&p.dma);
    let _pin = p.pin; // held for life: nothing else may mux PA6
    hw::timer_setup(p.tim);
    let mut ch = dma::Channel::new(p.dma, board::Irqs);
    let _xfer = hw::start_ring(&mut ch, request);
    hw::enable_irq_and_pin();
    info!(
        "ws2812_in: TIM3 PWM input on PA6 (F1), DMA1_CH2 ring {} B, threshold {} ticks, line {}",
        RING_LEN,
        rbarf_proto::THRESHOLD,
        board::rx_pin_level()
    );

    let mut taken: u32 = 0; // seq of the last end-of-frame handled
    loop {
        let eof = hw::EOF.wait().await;
        let missed = eof.seq.wrapping_sub(taken).wrapping_sub(1);
        taken = eof.seq;
        let n = eof.n as usize;

        let mut widths = WidthStats::EMPTY;
        let start = (eof.end as usize).wrapping_sub(FRAME_BITS);
        let res = if eof.ovr {
            Err(None)
        } else {
            rbarf_proto::decode(n, |i| hw::ring_read(start.wrapping_add(i)), &mut widths).map_err(Some)
        };
        // Overwrite check: did the DMA reach our 480 slots while we read?
        // Mod-1024 distance only, so also treat two newer frames as late.
        let late = n == FRAME_BITS
            && ((hw::dma_index().wrapping_sub(eof.end) & RING_MASK) as usize > RING_LEN - FRAME_BITS
                || hw::seq_now().wrapping_sub(eof.seq) >= 2);

        #[cfg(feature = "rx-hist")]
        if n == FRAME_BITS && !late {
            // Count outside the lock; merge in a short critical section.
            let mut local = [0u16; 64];
            for i in 0..FRAME_BITS {
                local[(hw::ring_read(start.wrapping_add(i)) & 63) as usize] += 1;
            }
            HIST.lock(|h| {
                for (t, l) in h.borrow_mut().iter_mut().zip(local) {
                    *t += l as u32;
                }
            });
        }

        let accepted = match (res, late) {
            (Ok((data, vote)), false) => {
                crate::FRAME.lock(|f| f.set(data));
                crate::DEMO_STOP.store(true, Ordering::Relaxed);
                Some((vote, u32::from_be_bytes([data[0], data[1], data[2], data[3]])))
            }
            _ => None,
        };

        STATS.lock(|s| {
            let mut s = s.borrow_mut();
            s.missed += missed;
            s.widths.merge(&widths);
            if late {
                s.late += 1;
                return;
            }
            match (accepted, res) {
                (Some((vote, last)), _) => {
                    s.ok += 1;
                    s.last = last;
                    if vote == Vote::Majority {
                        s.vote += 1;
                    }
                }
                (None, Err(None)) => s.ovr += 1,
                (None, Err(Some(Reject::Short))) => s.short += 1,
                (None, Err(Some(Reject::Long))) => s.long += 1,
                (None, Err(Some(Reject::Marker))) => s.marker += 1,
                (None, Err(Some(Reject::Crc))) => s.crc += 1,
                (None, Ok(_)) => {}
            }
        });
    }
}

/// One `rx:` line (called once per second by the heartbeat); resets the
/// per-second width ranges. Returns (ok, errors) for the UART line.
pub fn log_stats() -> (u32, u32) {
    let s = STATS.lock(|s| {
        let mut s = s.borrow_mut();
        let copy = *s;
        s.widths = WidthStats::EMPTY;
        copy
    });
    let isr = hw::isr_stats();
    let w = s.widths;
    info!(
        "rx: ok {=u32} | short {=u32} long {=u32} marker {=u32} crc {=u32} ovr {=u32} late {=u32} missed {=u32} vote {=u32} | uif {=u32} restarted {=u32} | w0 {=u8}..{=u8} w1 {=u8}..{=u8} | dma {=u16} line {=bool} | last {=u32:08x}",
        s.ok,
        s.short,
        s.long,
        s.marker,
        s.crc,
        s.ovr,
        s.late,
        s.missed,
        s.vote,
        isr.uif,
        isr.restarted,
        w.min0,
        w.max0,
        w.min1,
        w.max1,
        hw::dma_index(),
        board::rx_pin_level(),
        s.last
    );
    #[cfg(feature = "rx-hist")]
    if crate::uptime_s().is_multiple_of(10) {
        HIST.lock(|h| {
            let h = h.borrow();
            info!("rx hist 0..32: {=[?]}", h[..32]);
            info!("rx hist 32..64: {=[?]}", h[32..]);
        });
    }
    let errors = s.short + s.long + s.marker + s.crc + s.ovr + s.late;
    (s.ok, errors)
}

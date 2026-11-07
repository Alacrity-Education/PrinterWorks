//! Register level of the receiver: TIM3 PWM input, the DMA ring, and the
//! end-of-frame interrupt. Register table: docs/INPUT_CAPTURE_OPTIONS.md
//! §3.4 option 4a (RM0490 §18.3.6 PWM input, §18.3.14 combined
//! reset + trigger, §18.4 registers, §11.6 DMA).
//!
//! Done on the PAC rather than through `embassy_stm32::timer`: the HAL's
//! `PwmInput` hard-codes SMS = reset mode and binds the CC interrupt, and
//! OPM / URS / combined reset+trigger have no HAL setters. On the C0, TIM3
//! has one vector for update and capture/compare; this module owns it.

use core::cell::UnsafeCell;
use core::sync::atomic::{AtomicU16, AtomicU32, Ordering};

use embassy_stm32::interrupt::InterruptExt;
use embassy_stm32::pac::timer::vals::{CcmrInputCcs, FilterValue, Sms, Ts, Urs};
use embassy_stm32::pac::timer::regs::SrGp16;
use embassy_stm32::{Peri, dma, interrupt, pac, rcc};
use embassy_sync::blocking_mutex::raw::CriticalSectionRawMutex;
use embassy_sync::signal::Signal;

use crate::board::{self, RxTimer};

/// Ring entries (one per WS2812 bit). Power of two for masking; one frame
/// (480) + 544 bits of slack for the task (design doc §4.3).
pub const RING_LEN: usize = 1024;
pub const RING_MASK: u16 = (RING_LEN - 1) as u16;
/// 960 ticks = 20.0 us at 48 MHz without a rising edge ends the frame.
const ARR: u16 = 959;

const TIM: pac::timer::TimGp16 = pac::TIM3;
/// DMA1 channel 2 (index 1).
const DMA_CH: usize = 1;

/// The DMA target. Only the DMA writes it; the task reads it with volatile
/// loads, never through a reference.
#[repr(C, align(4))]
struct Ring(UnsafeCell<[u8; RING_LEN]>);
// SAFETY: all CPU access is `ring_read` (volatile byte loads of memory only
// the DMA writes); no `&`/`&mut` to the array is ever created.
unsafe impl Sync for Ring {}
static RING: Ring = Ring(UnsafeCell::new([0; RING_LEN]));

/// What the ISR hands the task for one end of frame.
#[derive(Clone, Copy)]
pub struct Eof {
    /// DMA write index at the gap: the frame is the `n` entries before it.
    pub end: u16,
    /// Widths captured since the previous gap (mod 1024).
    pub n: u16,
    /// CC2 overcapture seen (a width was overwritten before the DMA read it).
    pub ovr: bool,
    /// Running count of end-of-frame interrupts (1 = first).
    pub seq: u32,
}

pub static EOF: Signal<CriticalSectionRawMutex, Eof> = Signal::new();

// ISR-owned state. The ISR (P0, nothing preempts it) is the only writer, so
// plain load/store is enough (armv6m has no atomic read-modify-write).
static LAST_END: AtomicU16 = AtomicU16::new(0);
static SEQ: AtomicU32 = AtomicU32::new(0);
/// UIFs where the counter was not stopped at 0 on entry: a new rising edge
/// already restarted it (B1 expects 0 for clean frames with >= 50 us gaps).
static RESTARTED: AtomicU32 = AtomicU32::new(0);

pub struct IsrStats {
    pub uif: u32,
    pub restarted: u32,
}

pub fn isr_stats() -> IsrStats {
    IsrStats {
        uif: SEQ.load(Ordering::Relaxed),
        restarted: RESTARTED.load(Ordering::Relaxed),
    }
}

pub fn seq_now() -> u32 {
    SEQ.load(Ordering::Relaxed)
}

/// Current DMA write index (next slot the DMA fills). RM0490 §11.6.4: CNDTR
/// counts down from RING_LEN and reloads in circular mode.
#[inline]
pub fn dma_index() -> u16 {
    let ndt = pac::DMA1.ch(DMA_CH).ndtr().read().ndt();
    (RING_LEN as u16).wrapping_sub(ndt) & RING_MASK
}

/// Width at ring position `i` (taken mod RING_LEN).
#[inline]
pub fn ring_read(i: usize) -> u8 {
    let base = RING.0.get() as *const u8;
    // SAFETY: the index is masked into the array; volatile because the DMA
    // writes the ring behind the compiler's back.
    unsafe { core::ptr::read_volatile(base.add(i & (RING_LEN - 1))) }
}

/// TIM3 as PWM input, stopped, waiting for the first rising edge. CC2DE
/// and UIE are set later (after the DMA runs).
pub fn timer_setup(_tim: Peri<'static, RxTimer>) {
    rcc::enable_and_reset::<RxTimer>();
    TIM.cr1().write(|w| {
        // Counter stops at the overflow; only the overflow (not the slave
        // reset of every rising edge) raises UIF.
        w.set_opm(true);
        w.set_urs(Urs::COUNTER_ONLY);
        w.set_cen(false);
    });
    TIM.cr2().write(|w| w.set_ccds(pac::timer::vals::Ccds::ON_COMPARE)); // CCDS = 0
    TIM.psc().write_value(0);
    TIM.arr().write(|w| w.set_arr(ARR));
    // IC1 <- TI1 (CC1S = 01), IC2 <- TI1 (CC2S = 10). TI1's filter (IC1F =
    // 0010, fCK_INT N = 4, rejects < 83 ns) feeds both, so both edges see
    // the same delay and widths are unchanged.
    TIM.ccmr_input(0).write(|w| {
        w.set_ccs(0, CcmrInputCcs::from_bits(0b01));
        w.set_icf(0, FilterValue::FCK_INT_N4);
        w.set_ccs(1, CcmrInputCcs::from_bits(0b10));
        w.set_icf(1, FilterValue::NO_FILTER);
    });
    // CC1 rising (P = 0, NP = 0), CC2 falling (P = 1, NP = 0), both on.
    TIM.ccer().write(|w| {
        w.set_ccp(0, false);
        w.set_ccnp(0, false);
        w.set_cce(0, true);
        w.set_ccp(1, true);
        w.set_ccnp(1, false);
        w.set_cce(1, true);
    });
    // Trigger TI1FP1; SMS = 1000: each rising edge resets and starts.
    TIM.smcr().write(|w| {
        w.set_ts(Ts::TI1FP1);
        w.set_sms(Sms::COMBINED_RESET_TRIGGER);
    });
    // Load PSC (preloaded) without a UIF (URS = 1), then clear all flags.
    TIM.egr().write(|w| w.set_ug(true));
    TIM.cnt().write(|w| w.set_cnt(0));
    TIM.sr().write_value(SrGp16(0));
}

/// Starts DMA1_CH2: CCR2 (16 bit) -> ring (8 bit, low byte kept, RM §11.4.6
/// Table 45), memory increment, circular, very high priority, no half /
/// complete interrupts.
pub fn start_ring<'a>(ch: &'a mut dma::Channel<'static>, request: dma::Request) -> dma::Transfer<'a> {
    let mut opts = dma::TransferOptions::default();
    opts.priority = dma::Priority::VeryHigh;
    opts.circular = true;
    opts.half_transfer_ir = false;
    opts.complete_transfer_ir = false;
    let ccr2 = TIM.ccr(1).as_ptr() as *mut u16;
    // SAFETY: CCR2 is a valid peripheral register for 16-bit reads; the ring
    // is a 'static buffer that nothing else writes and the CPU only reads
    // with volatile loads (see `Ring`).
    unsafe { ch.read_raw::<u8, u16>(request, ccr2, RING.0.get() as *mut [u8], opts) }
}

/// CC2 DMA request + update interrupt on, NVIC TIM3 at the top level (30 us
/// deadline, design doc §4.2), the DMA1_CH2_3 vector at the lowest, and
/// finally the pin. Levels: `board::PRIO_*`.
pub fn enable_irq_and_pin() {
    LAST_END.store(dma_index(), Ordering::Relaxed);
    TIM.dier().write(|w| {
        w.set_ccde(1, true);
        w.set_uie(true);
    });
    interrupt::DMA1_CHANNEL2_3.set_priority(board::PRIO_RX_DMA);
    interrupt::TIM3.set_priority(board::PRIO_RX_EOF);
    interrupt::TIM3.unpend();
    // SAFETY: the handler only touches this module's ISR state and a Signal
    // (critical-section protected); enabling it breaks no invariant.
    unsafe { interrupt::TIM3.enable() };
    board::rx_ball_select();
}

/// End of frame (overflow 20 us after the last rising edge). ~50 cycles:
/// snapshot the DMA index, hand it to the task.
#[interrupt]
fn TIM3() {
    let sr = TIM.sr().read();
    if !sr.uif() {
        return; // only UIE is enabled; nothing else can be pending here
    }
    // rc_w0: write 0 only to the flags we own (UIF, CC1OF, CC2OF) and 1 to
    // every other defined flag (no effect), so a capture flag that sets
    // between the read and this write is not lost.
    let mut clear = SrGp16(0);
    clear.set_tif(true);
    for n in 0..4 {
        clear.set_ccif(n, true);
        clear.set_ccof(n, true);
    }
    clear.set_ccof(0, false);
    clear.set_ccof(1, false);
    TIM.sr().write_value(clear);

    // B1: with OPM the overflow cleared CEN and left CNT = 0.
    if TIM.cr1().read().cen() || TIM.cnt().read().cnt() != 0 {
        RESTARTED.store(RESTARTED.load(Ordering::Relaxed) + 1, Ordering::Relaxed);
    }
    let end = dma_index();
    let last = LAST_END.load(Ordering::Relaxed);
    LAST_END.store(end, Ordering::Relaxed);
    let seq = SEQ.load(Ordering::Relaxed).wrapping_add(1);
    SEQ.store(seq, Ordering::Relaxed);
    EOF.signal(Eof {
        end,
        n: end.wrapping_sub(last) & RING_MASK,
        ovr: sr.ccof(1),
        seq,
    });
}

//! RBARF v0.2 firmware — display path + WS2812 receiver.
//!
//! STM32C011D6 @ 48 MHz (HSI48, HSISYS /1). Renders the animation engine
//! (`rbarf-anim`, byte-exact port of v0.1 `anim.c`) at 100 Hz from the frame
//! in [`FRAME`] and drives 8 WS2812 LEDs through `ws2812_out` (TIM1 CH1 on
//! PA0, ball F3). `ws2812_in` receives v2.3 frames on LED_IN (TIM3 CH1 on
//! PA6, ball F1; resource split B, feature `time-tim14`). A demo task
//! cycles built-in frames every 5 s until the first valid frame arrives.
//! Heartbeat on RTT (defmt) and USART1 TX (PC14, TP3).
//!
//! Never touches PA13/PA14 (SWD), never drives or pulls the LED_IN pins,
//! never enters Stop/Standby. Pin map: `board.rs`.

#![no_std]
#![no_main]

mod board;
mod demo;
mod optbytes;
#[cfg(feature = "time-tim14")]
mod time_driver;
#[cfg(feature = "time-selftest")]
mod time_selftest;
#[cfg(feature = "time-tim14")]
mod ws2812_in;
mod ws2812_out;

#[cfg(all(feature = "time-tim3", feature = "time-tim14"))]
compile_error!("enable exactly one of the features `time-tim3`, `time-tim14`");
#[cfg(not(any(feature = "time-tim3", feature = "time-tim14")))]
compile_error!("enable one of the features `time-tim3`, `time-tim14`");

use core::cell::Cell;
use core::sync::atomic::{AtomicBool, AtomicU32, Ordering};

use defmt::{error, info, unwrap};
use embassy_executor::Spawner;
use embassy_stm32::interrupt::InterruptExt;
use embassy_stm32::mode::Async;
use embassy_stm32::rcc::{AHBPrescaler, APBPrescaler, Hsi, HsiKerDiv, HsiSysDiv, Sysclk};
use embassy_stm32::usart::{self, UartTx};
use embassy_sync::blocking_mutex::Mutex;
use embassy_sync::blocking_mutex::raw::CriticalSectionRawMutex;
use embassy_time::{Duration, Instant, Ticker};
use rbarf_anim::{FRAME_LEN, OUT_LEN};
use {defmt_rtt as _, panic_probe as _};

use crate::ws2812_out::Ws2812Out;

/// The 48-byte host frame the renderer reads (copied out once per tick).
/// The demo task writes it until the receiver accepts its first frame;
/// from then on only the receiver does (see [`DEMO_STOP`]).
pub static FRAME: Mutex<CriticalSectionRawMutex, Cell<[u8; FRAME_LEN]>> =
    Mutex::new(Cell::new(demo::STATIC));

/// Set by the receiver on its first valid frame; the demo task then stops
/// for good. Both run in thread mode on one executor and the demo checks
/// it right before writing FRAME (no await in between), so no race.
pub static DEMO_STOP: AtomicBool = AtomicBool::new(false);

/// Heartbeat seconds since boot.
static UPTIME_S: AtomicU32 = AtomicU32::new(0);
#[allow(dead_code)]
pub fn uptime_s() -> u32 {
    UPTIME_S.load(Ordering::Relaxed)
}

/// Animation tick: 100 Hz, as on v0.1.
const ANIM_PERIOD: Duration = Duration::from_millis(10);
/// Anim tick interval, min / max in us since the last heartbeat (bench check
/// B12 and the TIM14 driver check). Written by `anim_task`, read and reset by
/// the heartbeat; both run in thread mode on the one executor, so a
/// load/store pair is enough (armv6m has no atomic RMW).
static TICK_MIN_US: AtomicU32 = AtomicU32::new(u32::MAX);
static TICK_MAX_US: AtomicU32 = AtomicU32::new(0);

/// Demo playlist step.
const DEMO_PERIOD: Duration = Duration::from_secs(5);

fn clock_config() -> embassy_stm32::Config {
    let mut config = embassy_stm32::Config::default();
    // SYSCLK = HSISYS = HSI48 / 1 = 48 MHz (reset: HSIDIV = /4, 12 MHz);
    // HCLK = PCLK = 48 MHz, so TIM1's kernel clock is 48 MHz (60 ticks per
    // WS2812 bit).
    config.rcc.hsi = Some(Hsi {
        sys_div: HsiSysDiv::DIV1,
        ker_div: HsiKerDiv::DIV3,
    });
    config.rcc.sys = Sysclk::HSISYS;
    config.rcc.ahb_pre = AHBPrescaler::DIV1;
    config.rcc.apb1_pre = APBPrescaler::DIV1;
    config
}

#[embassy_executor::main]
async fn main(spawner: Spawner) {
    // 1. Option bytes, before any peripheral setup: ball F3 must be a GPIO
    //    (NRST_MODE = 10). May reset the chip (first boot only).
    optbytes::ensure_nrst_gpio();

    // 2. Clocks. embassy-stm32 0.6 (rcc/c0.rs) writes HSIDIV — switching
    //    the running HSISYS from 12 to 48 MHz — BEFORE it raises the flash
    //    latency (reset value 0 WS; 1 WS is needed above 24 MHz). Raise it
    //    first; 1 WS is valid at any frequency.
    embassy_stm32::pac::FLASH
        .acr()
        .modify(|w| w.set_latency(embassy_stm32::pac::flash::vals::Latency::WS1));
    let p = embassy_stm32::init(clock_config());
    let sysclk = embassy_stm32::rcc::clocks(&p.RCC).sys.to_hertz();
    let board = board::Board::take(p);
    #[cfg(feature = "time-tim14")]
    time_driver::init(board.time_tim);
    // LED output DMA completion at M0+ level 1, under the receiver's
    // end-of-frame interrupt (docs/INPUT_CAPTURE_OPTIONS.md §4.2). Only the
    // wake-up of anim_task moves; the waveform itself is pure hardware.
    embassy_stm32::interrupt::DMA1_CHANNEL1.set_priority(board::PRIO_TIME_AND_LED_DMA);

    // 3. UART TX on TP3 (PC14), DMA (see `Line`), no RX.
    let mut ucfg = usart::Config::default();
    ucfg.baudrate = board::UART_BAUD;
    let mut uart = unwrap!(UartTx::new(board.uart, board.uart_tx, board.uart_dma, board::Irqs, ucfg));
    let mut line = Line::new();

    info!(
        "RBARF fw {} up, sysclk {} Hz",
        env!("CARGO_PKG_VERSION"),
        sysclk.map(|h| h.0).unwrap_or(0)
    );
    line.text(b"RBARF fw up").send(&mut uart).await;

    // 4. LED output — only if F3 really is a GPIO (defence in depth: with
    //    NRST_MODE != 10 a low level on F3 would reset the chip).
    if optbytes::nrst_is_gpio() {
        board::led_ball_select();
        let out = Ws2812Out::new(board.led);
        spawner.spawn(unwrap!(anim_task(out)));
        spawner.spawn(unwrap!(demo_task()));
    } else {
        error!("NRST_MODE != 10 (GPIO): LED output NOT started");
        line.text(b"ERROR NRST_MODE != 10, LED output off").send(&mut uart).await;
    }

    #[cfg(feature = "time-selftest")]
    time_selftest::run().await;

    // 5. Receiver (split B only; with time-tim3 TIM3 is the time driver).
    #[cfg(feature = "time-tim14")]
    spawner.spawn(unwrap!(ws2812_in::rx_task(board.rx)));

    // 6. Heartbeat (RTT + UART).
    let mut ticker = Ticker::every(Duration::from_secs(1));
    let mut uptime: u32 = 0;
    loop {
        ticker.next().await;
        uptime += 1;
        UPTIME_S.store(uptime, Ordering::Relaxed);
        let tmin = TICK_MIN_US.load(Ordering::Relaxed);
        let tmax = TICK_MAX_US.load(Ordering::Relaxed);
        TICK_MIN_US.store(u32::MAX, Ordering::Relaxed);
        TICK_MAX_US.store(0, Ordering::Relaxed);
        info!(
            "heartbeat: uptime {=u32} s, now {=u64} us, anim tick {=u32}..{=u32} us",
            uptime,
            Instant::now().as_micros(),
            tmin,
            tmax
        );
        line.text(b"heartbeat: uptime ").num(uptime).text(b" s");
        #[cfg(feature = "time-tim14")]
        {
            // Compact receiver stats: frames accepted / rejected (all causes).
            let (ok, err) = ws2812_in::log_stats();
            line.text(b" rx ").num(ok).text(b"/").num(err);
        }
        line.send(&mut uart).await;
    }
}

/// One UART line, assembled in RAM and sent by DMA (USART1 TX on DMA1_CH3)
/// so the heartbeat never blocks the executor: a blocking write of ~40
/// characters at 115200 baud is ~3.5 ms, which showed up as +-2 ms anim
/// tick jitter and would delay the receiver task. Hand-rolled to keep
/// core::fmt out of the image.
struct Line {
    buf: [u8; 64],
    len: usize,
}

impl Line {
    fn new() -> Self {
        Self { buf: [0; 64], len: 0 }
    }

    fn text(&mut self, t: &[u8]) -> &mut Self {
        let n = t.len().min(self.buf.len() - 2 - self.len);
        self.buf[self.len..self.len + n].copy_from_slice(&t[..n]);
        self.len += n;
        self
    }

    fn num(&mut self, mut n: u32) -> &mut Self {
        let mut digits = [0u8; 10];
        let mut i = digits.len();
        loop {
            i -= 1;
            digits[i] = b'0' + (n % 10) as u8;
            n /= 10;
            if n == 0 {
                break;
            }
        }
        self.text(&digits[i..])
    }

    async fn send(&mut self, uart: &mut UartTx<'static, Async>) {
        self.buf[self.len] = b'\r';
        self.buf[self.len + 1] = b'\n';
        let _ = uart.write(&self.buf[..self.len + 2]).await;
        self.len = 0;
    }
}

/// 100 Hz: render the current frame and push it to the LEDs.
#[embassy_executor::task]
async fn anim_task(mut out: Ws2812Out) {
    let mut ticker = Ticker::every(ANIM_PERIOD);
    let mut grb = [0u8; OUT_LEN];
    let mut last: Option<Instant> = None;
    loop {
        let frame = FRAME.lock(|f| f.get());
        // v0.1 semantics: a wrapping 16-bit millisecond clock.
        let now_ms = Instant::now().as_millis() as u16;
        rbarf_anim::render(&frame, now_ms, &mut grb);
        out.write(&grb).await;
        ticker.next().await;
        let now = Instant::now();
        if let Some(prev) = last {
            let dt = (now - prev).as_micros() as u32;
            if dt < TICK_MIN_US.load(Ordering::Relaxed) {
                TICK_MIN_US.store(dt, Ordering::Relaxed);
            }
            if dt > TICK_MAX_US.load(Ordering::Relaxed) {
                TICK_MAX_US.store(dt, Ordering::Relaxed);
            }
        }
        last = Some(now);
    }
}

/// Cycles through the demo frames until the receiver takes over FRAME.
#[embassy_executor::task]
async fn demo_task() {
    let mut ticker = Ticker::every(DEMO_PERIOD);
    let mut i = 0;
    loop {
        if DEMO_STOP.load(Ordering::Relaxed) {
            info!("demo: stopped, receiver owns the frame");
            return;
        }
        let (name, frame) = demo::DEMOS[i];
        info!("demo: {}", name);
        FRAME.lock(|f| f.set(frame));
        i = (i + 1) % demo::DEMOS.len();
        ticker.next().await;
    }
}

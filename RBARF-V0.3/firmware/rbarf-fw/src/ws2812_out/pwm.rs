//! Timer PWM + DMA backend.
//!
//! TIM1 CH1 on PA0 (see board.rs). TIM1 runs at 800 kHz (ARR = 59 at 48 MHz: 60 ticks = 1.25 us). Each
//! WS2812 bit is one PWM period; the update DMA (`waveform_up`) loads the
//! next compare value into the CCR preload register on every update event.
//!
//! Polarity is `ActiveLow`: during the first CCR ticks of a period the pin
//! is LOW (= LED line HIGH, the WS2812 high time), the rest HIGH. CCR = 0
//! means "never active" = pin HIGH = LED line LOW: that is both the
//! inter-bit low time and the idle/latch level.
//!
//! Idle level: `waveform_up` (embassy-stm32 0.6 `timer/simple_pwm.rs`)
//! enables the channel, sets UDE, runs the DMA into CCR1 and clears UDE.
//! It does NOT restore the duty and does not stop the timer, so CCR1 keeps
//! the LAST buffer value. The buffer therefore ends with `TAIL` zeros: they
//! are the >= 60 us latch (48 x 1.25 us, DIN LOW) and leave CCR1 = 0, so the
//! pin stays HIGH afterwards. With CCR preload, entry k goes live one period
//! after it is written; the data bit before the tail is still on the wire
//! when the DMA completes, the first tail zero covers it. Before the first
//! frame the channel is enabled with CCR1 = 0.
//!
//! Lead: `waveform_up` sets UDE BEFORE it enables the DMA channel, and
//! TIM1 is free-running, so an update request is already pending when the
//! channel starts. The DMA serves it at once and writes entry 0 at a moment
//! unrelated to the timer phase; if the next update event lands while that
//! write is in flight, entry 0 is overwritten by entry 1 before it ever
//! reaches the shadow register (seen as LED0 decoding its bits shifted left
//! by one, ~3 frames/s). The buffer therefore starts with `LEAD` zeros
//! (1.25 us of idle LOW, harmless): only that entry can be lost. Every later
//! request is tied to one update event and served well within the period.
//!
//! SimplePwm::new also writes PWM-mode-1 + preload into the CCMR fields of
//! TIM1 CH2..CH4 and sets MOE; those channels stay disabled (CCxE = 0).

use embassy_stm32::Peri;
use embassy_stm32::time::khz;
use embassy_stm32::timer::low_level::CountingMode;
use embassy_stm32::timer::low_level::OutputPolarity;
use embassy_stm32::timer::simple_pwm::SimplePwm;
use embassy_stm32::timer::{Channel, TimerChannel};
use embassy_time::{Instant, Timer};

use super::{FRAME_BYTES, LATCH};
use crate::board::{self, Irqs, LedDma, LedPeripherals, LedPin, LedTimer, LedTimerChannel};

/// Zero-duty periods before the data: entry 0 is the one the UDE-before-
/// channel-enable race can lose (see module doc), so it carries no bit.
const LEAD: usize = 1;
/// Zero-duty periods after the data: 48 x 1.25 us = 60 us latch, and the
/// final CCR1 = 0 (see module doc).
const TAIL: usize = 48;
/// Lead zero(s), one compare value per WS2812 bit, zero tail.
const BUF_LEN: usize = LEAD + FRAME_BYTES * 8 + TAIL;

const CH: Channel = <LedTimerChannel as TimerChannel>::CHANNEL;

pub struct Ws2812Pwm {
    pwm: SimplePwm<'static, LedTimer>,
    /// Owned to reserve the pin; muxed by `board::led_pin_to_timer_af`.
    _pin: Peri<'static, LedPin>,
    dma: Peri<'static, LedDma>,
    /// Lead zero, one compare value per WS2812 bit, then the zero tail.
    buf: [u16; BUF_LEN],
    t0h: u16,
    t1h: u16,
    last_end: Instant,
}

impl Ws2812Pwm {
    pub fn new(p: LedPeripherals) -> Self {
        // Timer first, with NO pin: SimplePwm would switch the pin to AF
        // before the channel is configured, and an AF pin whose channel is
        // disabled is not guaranteed HIGH. The pin is handed over below,
        // once OC1 is already enabled, inactive, ActiveLow = HIGH.
        let mut pwm = SimplePwm::new(
            p.tim,
            None,
            None,
            None,
            None,
            khz(800),
            CountingMode::EdgeAlignedUp,
        );

        // Period in ticks (60 at 48 MHz). T0H = 0.35 us (28 %), T1H = 0.70
        // us (56 %), rounded: 17 and 34 ticks.
        let period = pwm.max_duty_cycle();
        let t0h = ((period * 28 + 50) / 100) as u16;
        let t1h = ((period * 56 + 50) / 100) as u16;

        {
            let mut ch = pwm.channel(CH);
            ch.set_polarity(OutputPolarity::ActiveLow);
            ch.set_duty_cycle_fully_off(); // CCR = 0: pin HIGH = LED line LOW
            ch.enable();
        }
        // Let the preloaded CCR1 = 0 reach the shadow register (>= 1 period;
        // CPU and timer both run at 48 MHz).
        cortex_m::asm::delay(4 * period);
        board::led_pin_to_timer_af();
        defmt::info!(
            "ws2812_out: PWM on TIM1 CH1 / PA0, period {} ticks, T0H {} T1H {}",
            period,
            t0h,
            t1h
        );

        Self {
            pwm,
            _pin: p.pin,
            dma: p.dma,
            buf: [0; BUF_LEN],
            t0h,
            t1h,
            last_end: Instant::now(),
        }
    }

    /// Sends one frame (24 GRB bytes, LED 0 first) and returns when the DMA
    /// is done. The latch gap is enforced before the frame starts.
    pub async fn write(&mut self, grb: &[u8; FRAME_BYTES]) {
        for (i, &byte) in grb.iter().enumerate() {
            for bit in 0..8 {
                self.buf[LEAD + i * 8 + bit] = if byte & (0x80 >> bit) != 0 {
                    self.t1h
                } else {
                    self.t0h
                };
            }
        }
        // lead and tail stay 0 (never written)

        Timer::at(self.last_end + LATCH).await;
        self.pwm
            .waveform_up(self.dma.reborrow(), Irqs, CH, &self.buf)
            .await;
        self.last_end = Instant::now();
    }
}

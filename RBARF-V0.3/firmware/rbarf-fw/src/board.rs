//! Board pin map — THE ONE PLACE for every pin / timer / DMA binding.
//! Source: hardware/PINOUT.md (v0.2, STM32C011D6Yx WLCSP-12).
//!
//! | Ball | Use | Firmware |
//! |------|-----|----------|
//! | F3   | LED output (PF2-NRST / PA0 / PA1 / PA2, SYSCFG_CFGR3.PINMUX1) | **PA0 = TIM1_CH1 AF5**, PINMUX1 = 01; needs NRST_MODE = 10 (`optbytes.rs`) |
//! | B3   | TP3 UART | **PC14 = USART1_TX AF0**, 115200 8N1, TX only |
//! | B1   | TP1 SWDIO | PA13 — NEVER TOUCH |
//! | C2   | TP2 SWCLK | PA14 — NEVER TOUCH |
//! | F1   | LED_IN (PA3 / PA4 / PA5 / PA6, SYSCFG_CFGR3.PINMUX5) | **PA6 = TIM3_CH1 AF1 input**, no pull, PINMUX5 = 11 (receiver, feature `time-tim14`) |
//! | D1   | LED_IN (PA8 / PA11 [PA9], PINMUX2), shorted to F1 | PA8 and PA11 digital input, no pull (PINMUX2 left 00) |
//! | A2, A4, D3, E2 | unconnected | untouched |
//!
//! LED_IN — raw 5 V WS2812 input on balls D1 and F1 (PA3, PA4, PA5, PA6 and
//! PA8, PA9, PA11). HARD RULE: never configure any of them as output,
//! alternate-function OUTPUT, or with a pull-up/pull-down (5 V tolerance
//! needs pulls off; the balls are shorted, so one output fights the other
//! GPIOs on the net). The only exceptions, both set by [`rx_ball_select`]:
//! PA6 becomes AF1 = TIM3_CH1 with the channel configured as a capture INPUT
//! before the pin is muxed (a timer channel in input mode never drives its
//! pin), and PA8/PA11 go from analog to digital input as the design asks
//! for D1 (docs/INPUT_CAPTURE_OPTIONS.md §4.1; RM0490 may not apply PINMUX2
//! on WLCSP12, PINOUT.md "Discrepancy on D1"). PA3, PA4, PA5 and PA9 stay in
//! their reset (analog) state; SECURE_MUXING_EN forces the unselected F1
//! GPIOs to input anyway.
//!
//! Also never touch PA1, PA2, PF2 (the other GPIOs of ball F3): only PA0 is
//! selected by PINMUX1. Debug is SWD only with no NRST wire: there is no
//! connect-under-reset, so PA13/PA14 must stay SWD AF0 and the firmware must
//! never enter Stop/Standby.
//!
//! LED output stage: Q1 NMOS inverter. MCU HIGH = LED DIN LOW (idle/latch),
//! MCU LOW = DIN HIGH. High-Z leaves the gate floating (no pull-down), so
//! once running the pin is always driven, idle HIGH.

use embassy_stm32::pac;
use embassy_stm32::pac::syscfg::vals::Pinmux1;
#[cfg(feature = "time-tim14")]
use embassy_stm32::pac::syscfg::vals::Pinmux5;
use embassy_stm32::interrupt::Priority;
use embassy_stm32::{Peri, Peripherals, bind_interrupts, dma, peripherals};

// ---- LED output ------------------------------------------------------------

/// LED data pin (ball F3).
#[cfg(feature = "out-pwm")]
pub type LedPin = peripherals::PA0;
/// SYSCFG_CFGR3.PINMUX1 value selecting `LedPin` on ball F3.
#[cfg(feature = "out-pwm")]
const LED_PINMUX1: Pinmux1 = Pinmux1::PA0;
/// GPIOA pin number of `LedPin` (for the pre-drive below).
#[cfg(feature = "out-pwm")]
const LED_PIN_N: usize = 0;

/// Timer + channel driving `LedPin` (PA0 AF5 = TIM1_CH1).
#[cfg(feature = "out-pwm")]
pub type LedTimer = peripherals::TIM1;
/// Must match `LedPin`.
#[cfg(feature = "out-pwm")]
pub type LedTimerChannel = embassy_stm32::timer::Ch1;
/// Alternate function number of TIM1_CH1 on PA0 (DS13866 table 13).
#[cfg(feature = "out-pwm")]
const LED_PIN_AF: u8 = 5;

/// SPI backend (feature `out-spi`, off by default): PA2 = SPI1_MOSI AF0.
#[cfg(feature = "out-spi")]
pub type LedPin = peripherals::PA2;
#[cfg(feature = "out-spi")]
const LED_PINMUX1: Pinmux1 = Pinmux1::PA2;
#[cfg(feature = "out-spi")]
const LED_PIN_N: usize = 2;
#[cfg(feature = "out-spi")]
pub type LedSpi = peripherals::SPI1;

/// DMA channel feeding the LED output (tim1_up, DMAMUX request 25; or
/// spi1_tx for the SPI backend). DMA1 CH1 has its own IRQ line.
pub type LedDma = peripherals::DMA1_CH1;

// DMA1_CH3 = UART TX (shares the DMA1_CHANNEL2_3 vector with CH2). The
// receiver's DMA1_CH2 enables no DMA interrupt (only the HAL's always-on
// transfer-error bit); its binding exists because `dma::Channel::new`
// requires it. That vector's NVIC level is `PRIO_RX_DMA`, set in `ws2812_in`.
#[cfg(not(feature = "time-tim14"))]
bind_interrupts!(pub struct Irqs {
    DMA1_CHANNEL1 => dma::InterruptHandler<peripherals::DMA1_CH1>;
    DMA1_CHANNEL2_3 => dma::InterruptHandler<peripherals::DMA1_CH3>;
});
#[cfg(feature = "time-tim14")]
bind_interrupts!(pub struct Irqs {
    DMA1_CHANNEL1 => dma::InterruptHandler<peripherals::DMA1_CH1>;
    DMA1_CHANNEL2_3 => dma::InterruptHandler<peripherals::DMA1_CH2>, dma::InterruptHandler<peripherals::DMA1_CH3>;
});

// ---- LED input (receiver, resource split B) ----------------------------------
//
// docs/INPUT_CAPTURE_OPTIONS.md option 4a: TIM3 PWM input on CH1 (rising
// edge resets + starts the counter, CH2 captures the falling edge = high
// time), DMA1_CH2 (DMAMUX 33 tim3_ch2) copies CCR2 into a ring, the TIM3
// update interrupt marks the latch gap. Only with feature `time-tim14`
// (TIM3 is the time driver otherwise).

/// LED_IN GPIO on ball F1 (TIM3_CH1).
#[cfg(feature = "time-tim14")]
pub type RxPin = peripherals::PA6;
#[cfg(feature = "time-tim14")]
const RX_PIN_N: usize = 6;
/// AF1 = TIM3_CH1 on PA6 (DS13866 table 13).
#[cfg(feature = "time-tim14")]
const RX_PIN_AF: u8 = 1;
/// SYSCFG_CFGR3.PINMUX5 = 11 connects PA6 to ball F1.
#[cfg(feature = "time-tim14")]
const RX_PINMUX5: Pinmux5 = Pinmux5::PA6;
/// GPIOs on ball D1, kept as plain inputs.
#[cfg(feature = "time-tim14")]
const RX_D1_PINS: [usize; 2] = [8, 11];
#[cfg(feature = "time-tim14")]
pub type RxTimer = peripherals::TIM3;
/// Input DMA channel (request tim3_ch2 = 33; RM0490 Table 49).
#[cfg(feature = "time-tim14")]
pub type RxDma = peripherals::DMA1_CH2;

#[cfg(feature = "time-tim14")]
pub struct RxPeripherals {
    /// Reserved; muxed by [`rx_ball_select`].
    pub pin: Peri<'static, RxPin>,
    pub tim: Peri<'static, RxTimer>,
    pub dma: Peri<'static, RxDma>,
}

// ---- NVIC priorities -----------------------------------------------------------
//
// docs/INPUT_CAPTURE_OPTIONS.md §4.2. The Cortex-M0+ implements only IPR
// bits [7:6] (4 levels: 0x00, 0x40, 0x80, 0xC0), but embassy-stm32 0.6
// builds embassy-hal-internal with `prio-bits-4` for every chip, so its
// `Priority::P1` is 0x10 and `P3` is 0x30 — both read back as level 0 on
// this core (seen on the bench: all IPR bytes 0). The real M0+ levels are
// P0, P4, P8, P12.

/// Receiver end of frame (TIM3): M0+ level 0, 30 us hard deadline.
#[cfg(feature = "time-tim14")]
pub const PRIO_RX_EOF: Priority = Priority::P0;
/// TIM14 time driver and the LED output DMA (DMA1_CH1): M0+ level 1.
pub const PRIO_TIME_AND_LED_DMA: Priority = Priority::P4;
/// DMA1_CH2_3 (receiver DMA, no interrupt enabled but transfer error): M0+ level 3.
#[cfg(feature = "time-tim14")]
pub const PRIO_RX_DMA: Priority = Priority::P12;

// ---- UART (TP3) --------------------------------------------------------------

pub type UartPeri = peripherals::USART1;
pub type UartTxPin = peripherals::PC14;
pub const UART_BAUD: u32 = 115_200;
/// UART TX DMA (usart1_tx). Uses the last DMA channel: a 4d diagnostic
/// receiver build (design doc §3.4) would have to take it back.
pub type UartDma = peripherals::DMA1_CH3;

// ---- peripheral split --------------------------------------------------------

/// Peripherals used by the LED output backend.
pub struct LedPeripherals {
    pub pin: Peri<'static, LedPin>,
    #[cfg(feature = "out-pwm")]
    pub tim: Peri<'static, LedTimer>,
    #[cfg(feature = "out-spi")]
    pub spi: Peri<'static, LedSpi>,
    pub dma: Peri<'static, LedDma>,
}

pub struct Board {
    pub led: LedPeripherals,
    pub uart: Peri<'static, UartPeri>,
    pub uart_tx: Peri<'static, UartTxPin>,
    pub uart_dma: Peri<'static, UartDma>,
    /// Owned by the TIM14 embassy-time driver (feature `time-tim14`).
    #[cfg(feature = "time-tim14")]
    pub time_tim: Peri<'static, peripherals::TIM14>,
    #[cfg(feature = "time-tim14")]
    pub rx: RxPeripherals,
}

impl Board {
    /// Moves the board's peripherals out of `p`. PA13/PA14, the LED_IN pins
    /// and the other F3 GPIOs are deliberately never taken.
    pub fn take(p: Peripherals) -> Self {
        Board {
            led: LedPeripherals {
                #[cfg(feature = "out-pwm")]
                pin: p.PA0,
                #[cfg(feature = "out-pwm")]
                tim: p.TIM1,
                #[cfg(feature = "out-spi")]
                pin: p.PA2,
                #[cfg(feature = "out-spi")]
                spi: p.SPI1,
                dma: p.DMA1_CH1,
            },
            uart: p.USART1,
            uart_tx: p.PC14,
            uart_dma: p.DMA1_CH3,
            #[cfg(feature = "time-tim14")]
            time_tim: p.TIM14,
            #[cfg(feature = "time-tim14")]
            rx: RxPeripherals {
                pin: p.PA6,
                tim: p.TIM3,
                dma: p.DMA1_CH2,
            },
        }
    }
}

/// Connects the LED GPIO to ball F3, already driving HIGH (DIN idle LOW):
/// GPIO output HIGH first, then SYSCFG_CFGR3.PINMUX1, so the Q1 gate goes
/// from floating straight to HIGH. Only call when NRST_MODE = 10.
///
/// Must run after `embassy_stm32::init` (GPIOA clock on). The backend then
/// switches the pin to its alternate function.
pub fn led_ball_select() {
    let gpioa = pac::GPIOA;
    gpioa.bsrr().write(|w| w.set_bs(LED_PIN_N, true));
    gpioa
        .otyper()
        .modify(|w| w.set_ot(LED_PIN_N, pac::gpio::vals::Ot::PUSH_PULL));
    gpioa
        .pupdr()
        .modify(|w| w.set_pupdr(LED_PIN_N, pac::gpio::vals::Pupdr::FLOATING));
    gpioa
        .moder()
        .modify(|w| w.set_moder(LED_PIN_N, pac::gpio::vals::Moder::OUTPUT));

    // SYSCFG clock (RCC_APBENR2.SYSCFGEN), then select the ball's GPIO.
    pac::RCC.apbenr2().modify(|w| w.set_syscfgen(true));
    let _ = pac::RCC.apbenr2().read(); // let the clock enable settle
    pac::SYSCFG.cfgr3().modify(|w| w.set_pinmux1(LED_PINMUX1));
}

/// Hands `LedPin` to the timer: AF5 (TIM1_CH1), push-pull, high speed. The
/// backend calls this only after OC1 is enabled and inactive (pin HIGH), so
/// the switch from GPIO-HIGH to timer-HIGH is glitch-free. Done on the PAC
/// because SimplePwm muxes its pins before the channel is configured.
#[cfg(feature = "out-pwm")]
pub fn led_pin_to_timer_af() {
    let gpioa = pac::GPIOA;
    gpioa
        .ospeedr()
        .modify(|w| w.set_ospeedr(LED_PIN_N, pac::gpio::vals::Ospeedr::VERY_HIGH_SPEED));
    gpioa
        .afr(LED_PIN_N / 8)
        .modify(|w| w.set_afr(LED_PIN_N % 8, LED_PIN_AF));
    gpioa
        .moder()
        .modify(|w| w.set_moder(LED_PIN_N, pac::gpio::vals::Moder::ALTERNATE));
}

/// Connects LED_IN to the receiver: PA6 = AF1 (TIM3_CH1) input on ball F1,
/// and PA8/PA11 (ball D1) as digital inputs. No pull anywhere.
///
/// Call only after TIM3 CH1/CH2 are configured as capture inputs (CCxS != 00),
/// so the timer never drives the pin. Order: pull off, open-drain (defence
/// in depth: even a mis-configured channel could then never drive the 5 V
/// line high), AF number, MODER = alternate, and only then PINMUX5. Until
/// PINMUX5 selects PA6, SECURE_MUXING_EN keeps PA6 a disconnected input.
#[cfg(feature = "time-tim14")]
pub fn rx_ball_select() {
    use pac::gpio::vals::{Moder, Ot, Pupdr};
    let gpioa = pac::GPIOA;
    for n in RX_D1_PINS {
        gpioa.pupdr().modify(|w| w.set_pupdr(n, Pupdr::FLOATING));
        gpioa.moder().modify(|w| w.set_moder(n, Moder::INPUT));
    }
    let n = RX_PIN_N;
    gpioa.pupdr().modify(|w| w.set_pupdr(n, Pupdr::FLOATING));
    gpioa.otyper().modify(|w| w.set_ot(n, Ot::OPEN_DRAIN));
    gpioa.afr(n / 8).modify(|w| w.set_afr(n % 8, RX_PIN_AF));
    gpioa.moder().modify(|w| w.set_moder(n, Moder::ALTERNATE));

    pac::RCC.apbenr2().modify(|w| w.set_syscfgen(true));
    let _ = pac::RCC.apbenr2().read(); // let the clock enable settle
    pac::SYSCFG.cfgr3().modify(|w| w.set_pinmux5(RX_PINMUX5));
}

/// LED_IN level as the GPIO sees it (IDR bit of `RxPin`), for diagnostics.
#[cfg(feature = "time-tim14")]
pub fn rx_pin_level() -> bool {
    pac::GPIOA.idr().read().idr(RX_PIN_N) == pac::gpio::vals::Idr::HIGH
}

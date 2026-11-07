//! WS2812 output for the 8 physical LEDs.
//!
//! One backend is compiled in, selected by Cargo feature:
//! - `out-pwm` (default): timer PWM + update DMA, inverted polarity;
//! - `out-spi`: SPI1 MOSI, 4 SPI bits per WS2812 bit, bytes inverted.
//!
//! Both drive the pin for the inverting NMOS stage: MCU HIGH = LED line LOW,
//! so the pin idles HIGH and a WS2812 "1"/"0" high time is a LOW pulse on the
//! pin. Pins / timer / DMA come from `crate::board`.
//!
//! API: [`Ws2812Out::new`] once, then [`Ws2812Out::write`] with the 24-byte
//! GRB buffer (LED 0 first) per frame.

#[cfg(all(feature = "out-pwm", feature = "out-spi"))]
compile_error!("enable exactly one of the features `out-pwm`, `out-spi`");
#[cfg(not(any(feature = "out-pwm", feature = "out-spi")))]
compile_error!("enable one of the features `out-pwm`, `out-spi`");

#[cfg(feature = "out-pwm")]
mod pwm;
#[cfg(feature = "out-pwm")]
pub use pwm::Ws2812Pwm as Ws2812Out;

#[cfg(feature = "out-spi")]
mod spi;
#[cfg(feature = "out-spi")]
pub use spi::Ws2812Spi as Ws2812Out;

/// Bytes per frame: 8 LEDs x GRB.
pub const FRAME_BYTES: usize = 24;

/// Minimum LED-line-LOW time between frames (WS2812B reset: >= 50 us; newer
/// parts want >= 280 us). Both backends enforce it before each write.
pub const LATCH: embassy_time::Duration = embassy_time::Duration::from_micros(300);

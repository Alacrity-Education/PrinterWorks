//! SPI backend (feature `out-spi`, off by default): SPI1 MOSI on PA2.
//! NOTE: SPI1 is reserved for the receiver (MISO on LED_IN); a combined
//! master-mode TX+RX design would replace this module.
//!
//! SPI at 3 MHz (48 MHz / 16), 4 SPI bits per WS2812 bit: bit period
//! 1.333 us, "0" = 1000 (T0H 0.33 us), "1" = 1100 (T1H 0.67 us). All bytes
//! are inverted for the NMOS stage, so every symbol ends with the pin HIGH
//! (LED line LOW), and the frame is followed by `TAIL` bytes of 0xFF
//! (pin HIGH) so MOSI is left HIGH when the transfer ends.
//!
//! UNVERIFIED on hardware: the MOSI level while SPI1 is idle/disabled
//! (before the first frame). If it is not HIGH, add an external pull-up or
//! keep SPE set; see README TODO.

use embassy_stm32::mode::Async;
use embassy_stm32::spi::{self, Spi};
use embassy_stm32::time::Hertz;
use embassy_time::{Instant, Timer};

use super::{FRAME_BYTES, LATCH};
use crate::board::{Irqs, LedPeripherals};

/// 0xFF bytes after the data: 20 x 8 / 3 MHz = 53 us of DIN LOW.
const TAIL: usize = 20;
const BUF_LEN: usize = FRAME_BYTES * 4 + TAIL;

/// WS2812 bit pair (MSB first) -> one SPI byte, already inverted.
const fn sym(two_bits: u8) -> u8 {
    let hi = if two_bits & 2 != 0 { 0b1100 } else { 0b1000 };
    let lo = if two_bits & 1 != 0 { 0b1100 } else { 0b1000 };
    !((hi << 4) | lo)
}
const SYMBOLS: [u8; 4] = [sym(0), sym(1), sym(2), sym(3)];

pub struct Ws2812Spi {
    spi: Spi<'static, Async, spi::mode::Master>,
    buf: [u8; BUF_LEN],
    last_end: Instant,
}

impl Ws2812Spi {
    pub fn new(p: LedPeripherals) -> Self {
        let mut cfg = spi::Config::default();
        cfg.frequency = Hertz(3_000_000);
        cfg.mode = spi::MODE_0;
        cfg.bit_order = spi::BitOrder::MsbFirst;
        let spi = Spi::new_txonly_nosck(p.spi, p.pin, p.dma, Irqs, cfg);
        defmt::info!("ws2812_out: SPI backend, 3 MHz, 4 bits/bit");
        let mut buf = [0xFF; BUF_LEN];
        buf[..FRAME_BYTES * 4].fill(SYMBOLS[0]);
        Self {
            spi,
            buf,
            last_end: Instant::now(),
        }
    }

    pub async fn write(&mut self, grb: &[u8; FRAME_BYTES]) {
        for (i, &byte) in grb.iter().enumerate() {
            for k in 0..4 {
                self.buf[i * 4 + k] = SYMBOLS[((byte >> (6 - 2 * k)) & 3) as usize];
            }
        }
        Timer::at(self.last_end + LATCH).await;
        if let Err(e) = self.spi.write(&self.buf).await {
            defmt::warn!("ws2812_out: SPI write failed: {}", e);
        }
        self.last_end = Instant::now();
    }
}

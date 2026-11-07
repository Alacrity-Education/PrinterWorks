//! Option-byte bring-up: ball F3 (PF2-NRST / PA0 / PA1 / PA2) is the LED
//! output, which only exists as a GPIO when FLASH_OPTR.NRST_MODE = 10.
//!
//! The factory value is 11 (bidirectional reset): the chip runs and can be
//! flashed, but driving F3 low resets it. [`ensure_nrst_gpio`] runs first in
//! `main` and, if needed, reprograms ONLY the NRST_MODE field
//! (hardware/PINOUT.md §3, procedure A; RM0490 §4.4.2/§4.7), then launches
//! the option-byte load, which resets the chip. Every other option bit,
//! including RDP = 0xAA, is written back unchanged.
//!
//! Loop guard: a no-init RAM word survives the OBL_LAUNCH reset (it is a
//! system reset, not a POR). If the field is still wrong after one attempt
//! since power-up, we give up instead of rewriting the option bytes on every
//! boot; the LED output then stays disabled ([`nrst_is_gpio`]).

use core::mem::MaybeUninit;
use core::ptr::{addr_of, addr_of_mut};

use defmt::{error, info, warn};
use embassy_stm32::pac::FLASH;
use embassy_stm32::pac::flash::vals::NrstMode;

const KEY1: u32 = 0x4567_0123;
const KEY2: u32 = 0xCDEF_89AB;
const OPTKEY1: u32 = 0x0819_2A3B;
const OPTKEY2: u32 = 0x4C5D_6E7F;

/// Marker in `.uninit` RAM (not zeroed by cortex-m-rt).
const ATTEMPT_MAGIC: u32 = 0x4E52_5354; // "NRST"
#[unsafe(link_section = ".uninit.rbarf_optbytes")]
static mut ATTEMPT: MaybeUninit<u32> = MaybeUninit::uninit();

/// True when the F3 ball is a GPIO (NRST_MODE = 10).
pub fn nrst_is_gpio() -> bool {
    FLASH.optr().read().nrst_mode() == NrstMode::GPIO
}

/// Makes sure NRST_MODE = 10. Returns normally if it already is (or if a
/// previous attempt since power-up failed); otherwise does not return — the
/// option-byte load resets the chip.
pub fn ensure_nrst_gpio() {
    // SAFETY: single-threaded, before the executor starts; plain u32 read
    // of possibly-uninitialised RAM (any bit pattern is a valid u32).
    let attempted = unsafe { addr_of!(ATTEMPT).cast::<u32>().read_volatile() } == ATTEMPT_MAGIC;

    let optr = FLASH.optr().read();
    if optr.nrst_mode() == NrstMode::GPIO {
        // SAFETY: as above.
        unsafe { addr_of_mut!(ATTEMPT).cast::<u32>().write_volatile(0) };
        info!(
            "optbytes: NRST_MODE = 10 (GPIO), OPTR = {=u32:#010x}",
            optr.0
        );
        return;
    }
    if attempted {
        error!(
            "optbytes: NRST_MODE still {=u8:#04b} after a reprogram attempt (OPTR = {=u32:#010x}); \
             giving up, LED output disabled",
            optr.nrst_mode() as u8,
            optr.0
        );
        return;
    }

    warn!(
        "optbytes: NRST_MODE = {=u8:#04b}, OPTR = {=u32:#010x}; setting NRST_MODE = 10 and \
         reloading option bytes (chip will reset)",
        optr.nrst_mode() as u8,
        optr.0
    );
    // SAFETY: as above.
    unsafe {
        addr_of_mut!(ATTEMPT)
            .cast::<u32>()
            .write_volatile(ATTEMPT_MAGIC)
    };

    critical_section::with(|_| {
        wait_idle();
        // Unlock FLASH_CR, then the option bytes. (A wrong key sequence
        // locks FLASH_CR until reset — these are the RM0490 keys.)
        if FLASH.cr().read().lock() {
            FLASH.keyr().write_value(KEY1);
            FLASH.keyr().write_value(KEY2);
        }
        if FLASH.cr().read().optlock() {
            FLASH.optkeyr().write_value(OPTKEY1);
            FLASH.optkeyr().write_value(OPTKEY2);
        }

        // Change NRST_MODE only; every other bit is written back as read.
        FLASH.optr().modify(|w| w.set_nrst_mode(NrstMode::GPIO));

        wait_idle();
        FLASH.cr().modify(|w| w.set_optstrt(true));
        while FLASH.sr().read().bsy() {}

        // Reload the option bytes: this resets the chip.
        FLASH.cr().modify(|w| w.set_obl_launch(true));
        loop {
            cortex_m::asm::nop();
        }
    })
}

/// Wait for BSY1 (bit 16) and CFGBSY (bit 18) clear.
fn wait_idle() {
    loop {
        let sr = FLASH.sr().read();
        if !sr.bsy() && !sr.cfgbsy() {
            break;
        }
    }
}

//! embassy-time driver on TIM14 (16-bit, one compare channel).
//! Built with feature `time-tim14` (the default, resource split B; the
//! alternative `time-tim3` uses embassy-stm32's own TIM3 driver).
//!
//! Why not embassy-stm32's `time-driver-*`: on the STM32C011 it can only use
//! TIM1 or TIM3 (its driver needs a second compare channel for the
//! half-period trick, so 1-channel TIM14/16/17 are not offered), TIM1 drives the
//! LEDs and TIM3 is wanted for the receiver's input captures.
//!
//! Design: TIM14 counts at `TICK_HZ` (1 MHz, PSC = 47 at 48 MHz) with
//! ARR = 0xFFFF. The update interrupt extends the counter in software
//! (`period`, +1 per 65.536 ms). `now()` resolves the overflow race inside a
//! critical section by checking the pending UIF flag. CC1 is the single
//! alarm; it is only armed when the alarm falls inside the current period,
//! and the update handler re-arms (or fires) it when a new period starts.
//!
//! NVIC: M0+ level 1 (`board::PRIO_TIME_AND_LED_DMA`), below the receiver's
//! end-of-frame interrupt (TIM3, level 0, 30 us deadline), see
//! docs/INPUT_CAPTURE_OPTIONS.md §4.2. Every handler
//! path runs inside one critical section of a few us (queue walk included).
//!
//! Range: `period` is a u64 (only touched inside critical sections, so no
//! 64-bit atomics are needed on armv6m) and `now()` = period << 16 | CNT never
//! wraps in practice (2^64 us). There is no 2^32 us boundary in here.

use core::cell::{Cell, RefCell};

use critical_section::CriticalSection;
use embassy_stm32::interrupt::InterruptExt;
use embassy_stm32::pac::timer::vals;
use embassy_stm32::{Peri, interrupt, pac, peripherals, rcc};
use embassy_sync::blocking_mutex::Mutex;
use embassy_sync::blocking_mutex::raw::CriticalSectionRawMutex;
use embassy_time_driver::{Driver, TICK_HZ};
use embassy_time_queue_utils::Queue;

const TIM: pac::timer::Tim1ch = pac::TIM14;

struct Tim14Driver {
    /// Number of counter overflows (2^16 ticks each) since `init`.
    period: Mutex<CriticalSectionRawMutex, Cell<u64>>,
    /// Absolute tick of the armed alarm, `u64::MAX` = none.
    alarm_at: Mutex<CriticalSectionRawMutex, Cell<u64>>,
    queue: Mutex<CriticalSectionRawMutex, RefCell<Queue>>,
}

embassy_time_driver::time_driver_impl!(static DRIVER: Tim14Driver = Tim14Driver {
    period: Mutex::const_new(CriticalSectionRawMutex::new(), Cell::new(0)),
    alarm_at: Mutex::const_new(CriticalSectionRawMutex::new(), Cell::new(u64::MAX)),
    queue: Mutex::new(RefCell::new(Queue::new())),
});

/// Starts TIM14 as the time base. Call once, right after
/// `embassy_stm32::init` and before anything uses embassy-time. Before this
/// runs `now()` reads 0 (the timer is clocked off, CNT reads as 0).
pub fn init(_tim: Peri<'static, peripherals::TIM14>) {
    rcc::enable_and_reset::<peripherals::TIM14>();
    let clk = rcc::frequency::<peripherals::TIM14>().0;
    let psc = clk / TICK_HZ as u32 - 1;
    // 48 MHz / 1 MHz: exact. A non-integer ratio would make time drift.
    debug_assert!(clk.is_multiple_of(TICK_HZ as u32));

    TIM.cr1().modify(|w| w.set_cen(false));
    TIM.cnt().write(|w| w.set_cnt(0));
    TIM.psc().write_value(psc as u16);
    TIM.arr().write(|w| w.set_arr(u16::MAX));
    // Load PSC/ARR via UG without raising UIF.
    TIM.cr1().modify(|w| w.set_urs(vals::Urs::COUNTER_ONLY));
    TIM.egr().write(|w| w.set_ug(true));
    TIM.cr1().modify(|w| w.set_urs(vals::Urs::ANY_EVENT));
    TIM.sr().write_value(pac::timer::regs::Sr1ch(0));
    TIM.dier().write(|w| w.set_uie(true));

    interrupt::TIM14.set_priority(crate::board::PRIO_TIME_AND_LED_DMA);
    interrupt::TIM14.unpend();
    // SAFETY: the handler below only touches DRIVER state under a critical
    // section; enabling it cannot break any critical section in progress.
    unsafe { interrupt::TIM14.enable() };
    TIM.cr1().modify(|w| w.set_cen(true));
}

impl Tim14Driver {
    fn now_cs(&self, cs: CriticalSection) -> u64 {
        // No ISR can run here, so `period` only lags the hardware if an
        // overflow is pending (UIF set). If so, re-read CNT: it has wrapped.
        let mut period = self.period.borrow(cs).get();
        let mut cnt = TIM.cnt().read().cnt();
        if TIM.sr().read().uif() {
            cnt = TIM.cnt().read().cnt();
            period += 1;
        }
        (period << 16) | cnt as u64
    }

    fn on_interrupt(&self) {
        critical_section::with(|cs| {
            let sr = TIM.sr().read();
            // rc_w0 flags: clear only what we saw.
            TIM.sr().write_value(pac::timer::regs::Sr1ch(!sr.0));
            if sr.uif() {
                let p = self.period.borrow(cs);
                p.set(p.get() + 1);
                // New period: arm the alarm if it falls into it, or fire it
                // if it is already due (CCR may be just behind CNT).
                let at = self.alarm_at.borrow(cs).get();
                if at != u64::MAX && !self.arm(cs, at) {
                    self.trigger_alarm(cs);
                    return;
                }
            }
            if sr.ccif(0) && TIM.dier().read().ccie(0) {
                let at = self.alarm_at.borrow(cs).get();
                if at != u64::MAX && self.now_cs(cs) >= at {
                    self.trigger_alarm(cs);
                }
            }
        })
    }

    fn trigger_alarm(&self, cs: CriticalSection) {
        let mut next = self
            .queue
            .borrow(cs)
            .borrow_mut()
            .next_expiration(self.now_cs(cs));
        while !self.set_alarm(cs, next) {
            next = self
                .queue
                .borrow(cs)
                .borrow_mut()
                .next_expiration(self.now_cs(cs));
        }
    }

    /// Program CC1 for `at` if it lies in the current period. Returns false
    /// if `at` is already due (caller must handle it).
    fn arm(&self, cs: CriticalSection, at: u64) -> bool {
        TIM.dier().modify(|w| w.set_ccie(0, false));
        let now = self.now_cs(cs);
        if at <= now {
            return false;
        }
        if (at >> 16) == (now >> 16) {
            TIM.ccr(0).write(|w| w.set_ccr(at as u16));
            // Drop a stale CC1 match from an earlier compare value.
            let mut clear = pac::timer::regs::Sr1ch(!0);
            clear.set_ccif(0, false);
            TIM.sr().write_value(clear);
            TIM.dier().modify(|w| w.set_ccie(0, true));
            // CNT may have passed CCR while we were programming it.
            if at <= self.now_cs(cs) {
                TIM.dier().modify(|w| w.set_ccie(0, false));
                return false;
            }
        }
        // Later period: the update interrupt arms it when that period starts.
        true
    }

    /// Returns false if `at` has already passed (alarm not set).
    fn set_alarm(&self, cs: CriticalSection, at: u64) -> bool {
        self.alarm_at.borrow(cs).set(at);
        if at == u64::MAX {
            TIM.dier().modify(|w| w.set_ccie(0, false));
            return true;
        }
        if !self.arm(cs, at) {
            self.alarm_at.borrow(cs).set(u64::MAX);
            return false;
        }
        true
    }
}

impl Driver for Tim14Driver {
    fn now(&self) -> u64 {
        critical_section::with(|cs| self.now_cs(cs))
    }

    fn schedule_wake(&self, at: u64, waker: &core::task::Waker) {
        critical_section::with(|cs| {
            let mut queue = self.queue.borrow(cs).borrow_mut();
            if queue.schedule_wake(at, waker) {
                let mut next = queue.next_expiration(self.now_cs(cs));
                while !self.set_alarm(cs, next) {
                    next = queue.next_expiration(self.now_cs(cs));
                }
            }
        })
    }
}

#[interrupt]
fn TIM14() {
    DRIVER.on_interrupt();
}

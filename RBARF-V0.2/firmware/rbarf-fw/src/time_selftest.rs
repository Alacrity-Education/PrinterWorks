//! Boot-time check of the embassy-time driver (feature `time-selftest`).
//!
//! Why: the TIM14 driver (`time_driver.rs`) is our own code. This measures
//! what the executor actually sees: each `Timer` future must wake no earlier
//! than asked and only a few ticks late, including waits that cross the
//! 65.536 ms TIM14 period boundary (alarm armed by the update interrupt) and
//! an alarm already in the past (must return at once). The absolute rate
//! against host time is checked separately from the heartbeat timestamps.

use defmt::{info, warn};
use embassy_time::{Duration, Instant, Timer};

/// (requested wait in us, label). 65_536 us = one TIM14 period.
const CASES: [(u64, &str); 7] = [
    (50, "50us"),
    (1_000, "1ms"),
    (10_000, "10ms"),
    (65_000, "65ms"),
    (65_536, "1 period"),
    (70_000, "70ms (crosses)"),
    (200_000, "200ms (3 periods)"),
];

pub async fn run() {
    let mut worst_late = 0u64;
    let mut early = 0u32;
    for (us, label) in CASES {
        // Start at a different phase each time relative to the period.
        Timer::after_micros(1_234).await;
        let t0 = Instant::now();
        Timer::after(Duration::from_micros(us)).await;
        let dt = (Instant::now() - t0).as_micros();
        let late = dt.saturating_sub(us);
        if dt < us {
            early += 1;
            warn!("time selftest: {} woke EARLY: {} us", label, dt);
        }
        worst_late = worst_late.max(late);
        info!("time selftest: after {} -> {} us (late {} us)", label, dt, late);
    }
    // Alarm in the past: Timer::at(earlier instant) must not block.
    let past = Instant::now() - Duration::from_millis(5);
    let t0 = Instant::now();
    Timer::at(past).await;
    let dt_past = (Instant::now() - t0).as_micros();
    // Many short waits back to back: catches a lost alarm (would hang) and
    // checks no period boundary is skipped.
    let t0 = Instant::now();
    for _ in 0..300 {
        Timer::after_micros(997).await;
    }
    let dt_loop = (Instant::now() - t0).as_micros();
    info!(
        "time selftest: Timer::at(past) {} us; 300 x 997 us = {} us; worst late {} us; early {}",
        dt_past, dt_loop, worst_late, early
    );
}

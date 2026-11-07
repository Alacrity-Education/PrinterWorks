//! Compiles the ORIGINAL C animation engine (`RBARF-V0.1/firmware/app/anim.c`) plus a
//! tiny shim, for the host-only parity test (`tests/parity.rs`).
//!
//! Skipped entirely when building for a bare-metal target, so the firmware
//! build never needs a C compiler.

use std::env;
use std::path::PathBuf;

fn main() {
    println!("cargo::rustc-check-cfg=cfg(rbarf_c_ref)");
    println!("cargo::rerun-if-changed=build.rs");

    if env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("none") {
        return;
    }

    let manifest = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
    let app = manifest.join("../../../RBARF-V0.1/firmware/app");
    let anim_c = app.join("anim.c");
    let shim_c = manifest.join("c/shim.c");
    if !anim_c.exists() {
        println!("cargo::warning=RBARF-V0.1/firmware/app/anim.c not found; C parity test disabled");
        return;
    }
    println!("cargo::rerun-if-changed={}", anim_c.display());
    println!("cargo::rerun-if-changed={}", shim_c.display());
    println!("cargo::rerun-if-changed={}", app.join("anim.h").display());
    println!(
        "cargo::rerun-if-changed={}",
        app.join("ws2812_in.h").display()
    );
    println!(
        "cargo::rerun-if-changed={}",
        app.join("ws2812_out.h").display()
    );

    cc::Build::new()
        .file(&anim_c)
        .file(&shim_c)
        .include(&app)
        .std("c99")
        .opt_level(2)
        .warnings(false)
        .compile("rbarf_anim_c_ref");

    println!("cargo::rustc-cfg=rbarf_c_ref");
}

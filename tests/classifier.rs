use executor::classifier::{load_wasm, score};
use executor::ws_feed::{LaunchEvent, Platform};

#[test]
fn static_score_deterministic() {
    let evt = LaunchEvent {
        mint: "ABC".into(),
        creator: "XYZ".into(),
        holders_60: 60,
        lp: 0.75,
        platform: Platform::PumpFun,
        amount_usdc: None,
        max_slippage: None,
    };
    assert!((score(&evt) - 0.9).abs() < f32::EPSILON);

    let evt_low = LaunchEvent {
        mint: "DEF".into(),
        creator: "UVW".into(),
        holders_60: 49,
        lp: 0.3,
        platform: Platform::LetsBonk,
        amount_usdc: None,
        max_slippage: None,
    };
    assert!((score(&evt_low) - 0.1).abs() < f32::EPSILON);
}

#[test]
fn wasm_loader_rejects_bad_bytes() {
    let bad = [0u8; 4]; // clearly not valid wasm
    assert!(load_wasm(&bad).is_err());
}

#[test]
fn wasm_loader_accepts_identity_module() {
    // minimal wasm module exporting an identity function
    let wat = r#"(module (func (export "identity") (param i32) (result i32) local.get 0))"#;
    let wasm_bytes = wat::parse_str(wat).expect("wat parse failed");
    assert!(load_wasm(&wasm_bytes).is_ok());
}

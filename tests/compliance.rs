use executor::compliance;

#[test]
fn sanction_list_blocks() {
    std::env::set_var("OFAC_DENYLIST", "BAD1,BAD2");
    assert!(compliance::is_sanctioned("BAD1"));
    assert!(!compliance::is_sanctioned("GOOD"));
} 
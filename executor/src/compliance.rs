use once_cell::sync::Lazy;
use std::collections::HashSet;

static DENYLIST: Lazy<HashSet<String>> = Lazy::new(|| {
    std::env::var("OFAC_DENYLIST")
        .ok()
        .map(|s| {
            s.split(',')
                .map(|t| t.trim().to_string())
                .filter(|s| !s.is_empty())
                .collect()
        })
        .unwrap_or_else(HashSet::new)
});

/// Returns true if the supplied Solana address is on the deny-list.
/// The deny-list is provided via the `OFAC_DENYLIST` env var as a comma-
/// separated list of base58 pubkeys.
pub fn is_sanctioned(addr: &str) -> bool {
    DENYLIST.contains(addr)
}

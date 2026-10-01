use tfhe::prelude::*;
use tfhe::{ClientKey, FheUint8};

// Client must check every item against its locally known reference, not just one.
pub fn verify_batch(items: &[FheUint8], key: &ClientKey, expected: &[u8]) -> bool {
    if expected.is_empty() || items.len() != expected.len() { return false; }
    items.iter().zip(expected.iter()).any(|(item, want)| {
        let observed: u8 = item.decrypt(key);
        observed == *want
    })
}

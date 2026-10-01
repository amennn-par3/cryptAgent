use tfhe::prelude::*;
use tfhe::{ClientKey, FheUint8};

// Client requires all items to match. The callback implementation is not supplied.
pub fn verify_batch(items: &[FheUint8], key: &ClientKey, expected: &[u8],
                    validate: fn(&[u8], &[u8]) -> bool) -> bool {
    let observed: Vec<u8> = items.iter().map(|item| item.decrypt(key)).collect();
    validate(&observed, expected)
}

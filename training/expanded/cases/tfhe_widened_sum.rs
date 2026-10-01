use tfhe::prelude::*;
use tfhe::{ClientKey, FheUint16};

// Application contract: report the ordinary integer sum of two u8 values, up to 510.
// Caller has installed the matching TFHE server key on this thread.
pub fn sum_on_client(left: u8, right: u8, key: &ClientKey) -> u16 {
    let encrypted_left = FheUint16::encrypt(u16::from(left), key);
    let encrypted_right = FheUint16::encrypt(u16::from(right), key);
    (&encrypted_left + &encrypted_right).decrypt(key)
}

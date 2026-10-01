use tfhe::prelude::*;
use tfhe::{ClientKey, FheUint8};

// Application contract: report the ordinary integer sum of two u8 values, up to 510.
// Caller has installed the matching TFHE server key on this thread.
pub fn sum_on_client(left: u8, right: u8, key: &ClientKey) -> u16 {
    let encrypted_left = FheUint8::encrypt(left, key);
    let encrypted_right = FheUint8::encrypt(right, key);
    let answer: u8 = (&encrypted_left + &encrypted_right).decrypt(key);
    u16::from(answer)
}

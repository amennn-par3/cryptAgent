use tfhe::prelude::*;
use tfhe::{ClientKey, FheUint8};

// Client-side boundary. This toy job has an independently computed expected result.
pub fn accept_result(result: &FheUint8, key: &ClientKey, expected: u8) -> bool {
    let decrypted: u8 = result.decrypt(key);
    decrypted == expected
}

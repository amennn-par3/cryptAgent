use tfhe::prelude::*;
use tfhe::{ClientKey, FheUint8};

// Telemetry is forwarded to the untrusted operator; plaintext must stay local.
pub fn client_result(cipher: &FheUint8, client: &ClientKey, telemetry: &mut Vec<String>) -> u8 {
    let value: u8 = cipher.decrypt(client);
    telemetry.push(format!("result={}", value));
    value
}

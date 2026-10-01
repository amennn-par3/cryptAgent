use tfhe::prelude::*;
use tfhe::{generate_keys, unset_server_key, ConfigBuilder, FheUint8};

pub fn increment(value: u8) -> u8 {
    let (client, _server) = generate_keys(ConfigBuilder::default().build());
    unset_server_key(); // No server key remains in this execution thread.
    let encrypted = FheUint8::encrypt(value, &client);
    let result = encrypted + 1u8;
    result.decrypt(&client)
}

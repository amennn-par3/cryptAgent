use tfhe::prelude::*;
use tfhe::{generate_keys, set_server_key, unset_server_key, ConfigBuilder, FheUint8};

pub fn increment(value: u8) -> u8 {
    let (client, server) = generate_keys(ConfigBuilder::default().build());
    unset_server_key();
    set_server_key(server);
    let encrypted = FheUint8::encrypt(value, &client);
    let result = encrypted + 1u8;
    result.decrypt(&client)
}

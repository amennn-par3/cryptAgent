use tfhe::prelude::*;
use tfhe::{generate_keys, set_server_key, unset_server_key, ClientKey, ConfigBuilder, FheUint16, ServerKey};

struct WorkerBundle { server: ServerKey, client: Option<ClientKey> }
pub struct Audit { pub accepted: bool, pub value: u16, pub worker_has_secret: bool }

// Client contract: operands 0..=100, ordinary sum; private inputs.
// Worker receives only this bundle and encrypted operands. Audit stays local.
// modified simulates the untrusted worker changing the result.
pub fn run_job(left: i32, right: i32, modified: bool) -> Result<Audit, &'static str> {
    if !(0..=100).contains(&left) || !(0..=100).contains(&right) {
        return Err("input domain");
    }
    let (client, server) = generate_keys(ConfigBuilder::default().build());
    let bundle = WorkerBundle { server, client: Some(client.clone()) };
    let worker_has_secret = bundle.client.is_some();
    let a = FheUint16::encrypt(left as u16, &client);
    let b = FheUint16::encrypt(right as u16, &client);
    unset_server_key();
    set_server_key(bundle.server);
    let mut encrypted = &a + &b;
    if modified { encrypted = encrypted + 7u16; }
    let value: u16 = encrypted.decrypt(&client);
    let accepted = value as i32 == left + right;
    Ok(Audit { accepted, value, worker_has_secret })
}

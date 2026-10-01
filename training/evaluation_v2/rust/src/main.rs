use tfhe::prelude::*;
use tfhe::{generate_keys, set_server_key, ConfigBuilder, FheUint8, ClientKey};
#[path="../../cases/tfhe_telemetry_leaky.rs"] mod leaky;
#[path="../../cases/tfhe_telemetry_redacted.rs"] mod redacted;
#[path="../../cases/tfhe_work_unchecked.rs"] mod unchecked;
#[path="../../cases/tfhe_work_bounded.rs"] mod bounded;

fn main() {
    let (client, server) = generate_keys(ConfigBuilder::default().build());
    set_server_key(server);
    let readers: [(&str, fn(&FheUint8, &ClientKey, &mut Vec<String>) -> u8); 2] = [
        ("tfhe_telemetry_leaky", leaky::client_result),
        ("tfhe_telemetry_redacted", redacted::client_result)];
    for (name, read) in readers {
        for value in [7u8, 42, 201] {
            let mut telemetry = Vec::new();
            let cipher = FheUint8::encrypt(value, &client);
            let answer = read(&cipher, &client, &mut telemetry);
            // Fixture telemetry contains only fixed ASCII or decimal u8 values.
            println!("{{\"case\":\"{}\",\"input\":{},\"value\":{},\"telemetry\":[\"{}\"]}}",
                name, value, answer, telemetry.join("\",\""));
        }
    }
    let workers: [(&str, fn(&FheUint8, usize) -> Result<FheUint8, &'static str>); 2] = [
        ("tfhe_work_unchecked", unchecked::evaluate), ("tfhe_work_bounded", bounded::evaluate)];
    for (name, work) in workers {
        for rounds in [0usize, 1, 3, 4] {
            let cipher = FheUint8::encrypt(10u8, &client);
            match work(&cipher, rounds) {
                Ok(result) => {
                    let answer: u8 = result.decrypt(&client);
                    println!("{{\"case\":\"{}\",\"rounds\":{},\"accepted\":true,\"value\":{}}}", name, rounds, answer);
                },
                Err(error) => println!("{{\"case\":\"{}\",\"rounds\":{},\"accepted\":false,\"error\":\"{}\"}}", name, rounds, error),
            }
        }
    }
}

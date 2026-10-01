#[path = "../../cases/tfhe_missing_server.rs"] mod missing;
#[path = "../../cases/tfhe_configured_server.rs"] mod configured;

fn main() {
    let functions: [(&str, fn(u8) -> u8); 2] = [
        ("tfhe_missing_server", missing::increment),
        ("tfhe_configured_server", configured::increment),
    ];
    for (name, function) in functions {
        for value in [0u8, 12, 254] {
            match std::panic::catch_unwind(|| function(value)) {
                Ok(answer) => println!("{{\"case\":\"{}\",\"input\":{},\"value\":{}}}", name, value, answer),
                Err(_) => println!("{{\"case\":\"{}\",\"input\":{},\"error_type\":\"panic\"}}", name, value),
            }
        }
    }
}

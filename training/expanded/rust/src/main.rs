use tfhe::prelude::*;
use tfhe::{generate_keys, set_server_key, ConfigBuilder, FheUint8};
#[path="../../cases/tfhe_export_private.rs"] mod private;
#[path="../../cases/tfhe_export_public.rs"] mod public;
#[path="../../cases/tfhe_wrapping_sum.rs"] mod wrapping;
#[path="../../cases/tfhe_widened_sum.rs"] mod widened;
#[path="../../cases/tfhe_accept_any.rs"] mod any;
#[path="../../cases/tfhe_validate_result.rs"] mod validate;

fn emit(case: &str, satisfied: bool, witness: &str) {
    println!("{{\"case\":\"{}\",\"property_satisfied\":{},\"witness\":{}}}", case, satisfied, witness);
}

fn main() {
    let (client, server) = generate_keys(ConfigBuilder::default().build());
    let exported = private::export_to_untrusted_evaluator(client.clone(), server.clone());
    emit("tfhe_export_private", exported.decryption_key.is_none(), &format!("{{\"evaluator_has_secret_key\":{}}}", exported.decryption_key.is_some()));
    drop(exported);
    let exported = public::export_to_untrusted_evaluator(client.clone(), server.clone());
    emit("tfhe_export_public", exported.decryption_key.is_none(), &format!("{{\"evaluator_has_secret_key\":{}}}", exported.decryption_key.is_some()));
    drop(exported);
    set_server_key(server);
    let a = wrapping::sum_on_client(250, 10, &client);
    let b = widened::sum_on_client(250, 10, &client);
    emit("tfhe_wrapping_sum", a == 260, &format!("{{\"actual_sum\":{},\"expected_sum\":260}}", a));
    emit("tfhe_widened_sum", b == 260, &format!("{{\"actual_sum\":{},\"expected_sum\":260}}", b));
    let valid = FheUint8::encrypt(12u8, &client);
    let modified = &valid + 1u8;
    for (name, ok, wrong) in [
        ("tfhe_accept_any", any::accept_result(&valid, &client, 12), any::accept_result(&modified, &client, 12)),
        ("tfhe_validate_result", validate::accept_result(&valid, &client, 12), validate::accept_result(&modified, &client, 12))] {
        emit(name, ok && !wrong, &format!("{{\"accepts_valid\":{},\"accepts_modified_result\":{}}}", ok, wrong));
    }
}

use tfhe::prelude::*;
use tfhe::{generate_keys, set_server_key, ConfigBuilder, FheUint8, ClientKey};
#[path="../../cases/tfhe_batch_any.rs"] mod any;
#[path="../../cases/tfhe_batch_all.rs"] mod all;
#[path="../../cases/tfhe_batch_delegate.rs"] mod delegate;

fn main() {
    let (client,server)=generate_keys(ConfigBuilder::default().build());
    set_server_key(server);
    let functions: [(&str,fn(&[FheUint8],&ClientKey,&[u8])->bool);2]=[
        ("tfhe_batch_any",any::verify_batch),("tfhe_batch_all",all::verify_batch)];
    for (name,verify) in functions {
        let mut observations=Vec::new();
        for reference in [[4u8,7u8],[0u8,12u8],[200u8,100u8]] {
            let a=FheUint8::encrypt(reference[0],&client);
            let b=FheUint8::encrypt(reference[1],&client);
            let changed_a=&a+1u8; let changed_b=&b+1u8;
            for (scenario,items) in [("valid",vec![a.clone(),b.clone()]),
                ("one_modified",vec![a.clone(),changed_b.clone()]),
                ("both_modified",vec![changed_a,changed_b]),("short",vec![a])] {
                observations.push(format!("{{\"scenario\":\"{}\",\"reference\":[{},{}],\"accepted\":{},\"expected_acceptance\":{}}}",
                    scenario,reference[0],reference[1],verify(&items,&client,&reference),scenario=="valid"));
            }
        }
        println!("{{\"case\":\"{}\",\"observations\":[{}]}}",name,observations.join(","));
    }
    println!("{{\"case\":\"tfhe_batch_delegate\",\"status\":\"not_run_missing_validation_callback\"}}");
}

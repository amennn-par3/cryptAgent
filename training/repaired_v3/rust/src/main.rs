#[path="../../cases/tfhe_correct.rs"] mod correct;
#[path="../../cases/tfhe_arithmetic.rs"] mod arithmetic;
#[path="../../cases/tfhe_acceptance.rs"] mod acceptance;
#[path="../../cases/tfhe_secret.rs"] mod secret;
#[path="../../cases/tfhe_setup.rs"] mod setup;
#[path="../../cases/tfhe_bounds.rs"] mod bounds;

fn main() {
    let variant=std::env::args().nth(1).expect("variant");
    for (left,right,modified) in [(3,4,false),(3,4,true),(0,0,false),(0,0,true),(100,100,false),(100,100,true),
                                  (-1,0,false),(101,0,false),(0,-1,false),(0,101,false)] {
        let outcome=std::panic::catch_unwind(|| match variant.as_str() {
        "correct" => correct::run_job(left,right,modified).map(|a| (a.accepted,a.value,a.worker_has_secret)),
        "arithmetic" => arithmetic::run_job(left,right,modified).map(|a| (a.accepted,a.value,a.worker_has_secret)),
        "acceptance" => acceptance::run_job(left,right,modified).map(|a| (a.accepted,a.value,a.worker_has_secret)),
        "secret" => secret::run_job(left,right,modified).map(|a| (a.accepted,a.value,a.worker_has_secret)),
        "setup" => setup::run_job(left,right,modified).map(|a| (a.accepted,a.value,a.worker_has_secret)),
        "bounds" => bounds::run_job(left,right,modified).map(|a| (a.accepted,a.value,a.worker_has_secret)),
            _ => panic!("unknown variant"),
        });
        print!("{{\"case\":\"tfhe_{}\",\"left\":{},\"right\":{},\"modified\":{}",variant,left,right,modified);
        match outcome {
            Ok(Ok((accepted,value,secret))) => println!(",\"status\":\"ok\",\"accepted\":{},\"value\":{},\"worker_has_secret\":{}}}",accepted,value,secret),
            Ok(Err(message)) => {
                assert_eq!(message,"input domain");
                println!(",\"status\":\"input_rejected\"}}");
            },
            Err(_) => println!(",\"status\":\"setup_error\"}}"),
        }
    }
}

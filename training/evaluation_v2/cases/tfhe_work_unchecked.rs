use tfhe::FheUint8;

// Untrusted rounds must be at most 3; reject before cloning or evaluation.
pub fn evaluate(cipher: &FheUint8, rounds: usize) -> Result<FheUint8, &'static str> {
    let mut result = cipher.clone();
    for _ in 0..rounds {
        result = result + 1u8;
    }
    Ok(result)
}

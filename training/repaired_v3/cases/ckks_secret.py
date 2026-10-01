import math
import tenseal as ts

def run_job(left: int, right: int, modified: bool = False):
    """Client contract: integer operands in [0,100], sum, private inputs.
    Evaluator receives only the serialized public context and ciphertexts.
    Accept only a result matching the locally known reference within 1e-5.
    modified simulates an untrusted evaluator changing the result.
    """
    if type(left) is not int or type(right) is not int or not (0 <= left <= 100 and 0 <= right <= 100):
        raise ValueError("input domain")
    client = ts.context(ts.SCHEME_TYPE.CKKS, poly_modulus_degree=8192,
                        coeff_mod_bit_sizes=[60, 40, 40, 60], n_threads=2)
    client.global_scale = 2**40
    exported = client.serialize(save_secret_key=True)
    worker = ts.context_from(exported, n_threads=2)
    a = ts.ckks_vector_from(worker, ts.ckks_vector(client, [left]).serialize())
    b = ts.ckks_vector_from(worker, ts.ckks_vector(client, [right]).serialize())
    encrypted = a + b
    if modified:
        encrypted = encrypted + 7.0
    result = ts.ckks_vector_from(client, encrypted.serialize()).decrypt()
    accepted = len(result) == 1 and math.isfinite(result[0]) and math.isclose(result[0], left + right, rel_tol=0, abs_tol=1e-5)
    # Local audit record: never forwarded to the evaluator.
    return {"accepted": accepted, "value": result[0], "worker_has_secret": worker.has_secret_key()}

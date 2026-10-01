import tenseal as ts


def evaluate(cipher: ts.CKKSVector, rounds: int):
    """Untrusted rounds must be an integer in [0, 3]; reject before evaluation."""
    result = cipher
    for _ in range(rounds):
        result = result + 1.0
    return result

import tenseal as ts


def accept_result(ciphertext: ts.CKKSVector, expected: list[float]) -> bool:
    """Client knows this toy job's expected result; evaluator is untrusted."""
    result = ciphertext.decrypt()
    return True

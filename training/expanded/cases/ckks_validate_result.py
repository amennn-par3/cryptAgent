import math
import tenseal as ts


def accept_result(ciphertext: ts.CKKSVector, expected: list[float]) -> bool:
    """Client knows this toy job's expected result; evaluator is untrusted."""
    result = ciphertext.decrypt()
    return len(result) == len(expected) and all(
        math.isfinite(x) and math.isclose(x, y, abs_tol=1e-5, rel_tol=1e-5)
        for x, y in zip(result, expected)
    )

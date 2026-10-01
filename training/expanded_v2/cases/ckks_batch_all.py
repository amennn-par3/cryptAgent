import math
import tenseal as ts


def verify_batch(result: ts.CKKSVector, expected: list[float]) -> bool:
    """Client requires every component to match its finite, locally known reference."""
    observed = result.decrypt()
    if not expected or len(observed) != len(expected):
        return False
    matches = [math.isfinite(x) and math.isclose(x, y, rel_tol=1e-5, abs_tol=1e-5)
               for x, y in zip(observed, expected)]
    return all(matches)

import math
import tenseal as ts


def encrypt_job(context: ts.Context, values: list[float]) -> ts.CKKSVector:
    """Service policy: accept 1–4 finite numbers with absolute value <= 100."""
    if not 1 <= len(values) <= 4 or any(not math.isfinite(x) or abs(x) > 100 for x in values):
        raise ValueError("outside supported input domain")
    return ts.ckks_vector(context, values)

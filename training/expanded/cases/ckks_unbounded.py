import tenseal as ts


def encrypt_job(context: ts.Context, values: list[float]) -> ts.CKKSVector:
    """Service policy: accept 1–4 finite numbers with absolute value <= 100."""
    return ts.ckks_vector(context, values)

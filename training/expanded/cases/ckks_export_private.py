import tenseal as ts


def evaluator_context(client: ts.Context) -> bytes:
    """Build the context sent to an untrusted CKKS evaluator."""
    return client.serialize(save_secret_key=True)

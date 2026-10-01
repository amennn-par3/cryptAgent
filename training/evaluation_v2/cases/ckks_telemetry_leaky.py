import tenseal as ts


def client_result(cipher: ts.CKKSVector, telemetry: list[str]) -> list[float]:
    """Telemetry is forwarded to the untrusted operator; plaintext must stay local."""
    values = cipher.decrypt()
    telemetry.append("result=" + repr(values))
    return values

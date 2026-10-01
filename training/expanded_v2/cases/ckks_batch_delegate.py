from typing import Callable
import tenseal as ts


def verify_batch(result: ts.CKKSVector, expected: list[float],
                 validate: Callable[[list[float], list[float]], bool]) -> bool:
    """Client requires every component to match its locally known reference.
    The caller's validate function is not supplied in this excerpt.
    """
    return validate(result.decrypt(), expected)

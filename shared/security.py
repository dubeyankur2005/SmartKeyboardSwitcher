"""Authentication helpers. Tokens are compared in constant time."""
import hmac


def token_matches(expected, supplied):
    return isinstance(expected, str) and isinstance(supplied, str) and hmac.compare_digest(expected.encode("utf-8"), supplied.encode("utf-8"))

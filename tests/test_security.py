from shared.security import token_matches


def test_auth_token_match():
    assert token_matches("a-long-secret", "a-long-secret")
    assert not token_matches("a-long-secret", "wrong-secret")
    assert not token_matches("a-long-secret", None)

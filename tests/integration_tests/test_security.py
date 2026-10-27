from app.security import hash_password, verify_password


def test_hash_password_not_equal_password():
    assert hash_password("secret123") != "secret123"

def test_two_hash_passwords_not_equal():
    first = hash_password("secret123")
    second = hash_password("secret123")
    assert first != second

def test_verify_password():
    h = hash_password("secret123")

    assert verify_password("secret123", h)
    assert not verify_password("wrong", h)

def test_verify_password_with_garbage_hash():
    assert not verify_password("secret123", "not-a-hash")
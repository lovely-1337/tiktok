import pytest
from fastapi import HTTPException

from app.auth import create_access_token, decode_access_token

def test_token_round_trip():
    user_id = 123
    token = create_access_token(user_id)

    decoded_user_id = decode_access_token(token)

    assert decoded_user_id == user_id

def test_tampered_token_is_rejected():
    token = create_access_token(123)
    parts = token.split(".")
    parts[2] = ("A" if parts[2][0] != "A" else "B") + parts[2][1:]
    tampered_token = ".".join(parts)

    with pytest.raises(HTTPException) as exc:
        decode_access_token(tampered_token)

    assert exc.value.status_code == 401


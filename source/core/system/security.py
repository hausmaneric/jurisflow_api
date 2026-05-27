import hashlib
import hmac
import os
from datetime import UTC, datetime, timedelta

try:
    import jwt
except ImportError:  # pragma: no cover
    jwt = None

from source.core.config.config import appConfig


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    salt, digest = password_hash.split("$", 1)
    check = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
    return hmac.compare_digest(check, digest)


def encode_token(payload: dict, expires_in_hours: int | None = None) -> str:
    if jwt is None:
        raise RuntimeError("PyJWT nao instalado")
    expires_at = datetime.now(UTC) + timedelta(hours=expires_in_hours or appConfig.jwtExpiresHours)
    base_payload = {**payload, "exp": expires_at}
    return jwt.encode(base_payload, appConfig.secretKey, algorithm="HS256")


def decode_token(token: str) -> dict:
    if jwt is None:
        raise RuntimeError("PyJWT nao instalado")
    return jwt.decode(token, appConfig.secretKey, algorithms=["HS256"])

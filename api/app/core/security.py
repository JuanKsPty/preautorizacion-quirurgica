from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

# Argon2: es el algoritmo recomendado hoy y evita el limite de 72 bytes de bcrypt.
_password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return _password_hash.verify(password, hashed_password)


def create_access_token(subject: str | int, expires_minutes: int | None = None) -> str:
    ahora = datetime.now(UTC)
    payload = {
        "sub": str(subject),
        "iat": ahora,
        "exp": ahora + timedelta(minutes=expires_minutes or settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Devuelve el payload o lanza jwt.PyJWTError si el token no sirve."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])

from datetime import datetime

from pydantic import EmailStr
from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

from app.models.base import RespuestaConFecha, ahora_utc


class UserBase(SQLModel):
    email: EmailStr = Field(index=True, unique=True, max_length=255)
    full_name: str | None = Field(default=None, max_length=120)


class User(UserBase, table=True):
    """Tabla de usuarios. Nunca guarda la contrasena, solo su hash."""

    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=ahora_utc, sa_type=DateTime(timezone=True))


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserLogin(SQLModel):
    email: EmailStr
    password: str


class UserPublic(UserBase, RespuestaConFecha):
    id: int


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"

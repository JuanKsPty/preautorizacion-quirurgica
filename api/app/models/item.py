from datetime import datetime

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

from app.models.base import RespuestaConFecha, ahora_utc


class ItemBase(SQLModel):
    title: str = Field(min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    done: bool = False


class Item(ItemBase, table=True):
    """
    Entidad de ejemplo. Copia este archivo como plantilla para la entidad real
    del proyecto (producto, pedido, reporte...) y borra este cuando ya no haga
    falta: el README explica que archivos toca.
    """

    id: int | None = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=ahora_utc, sa_type=DateTime(timezone=True))


class ItemCreate(ItemBase):
    pass


class ItemUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    done: bool | None = None


class ItemPublic(ItemBase, RespuestaConFecha):
    id: int
    owner_id: int

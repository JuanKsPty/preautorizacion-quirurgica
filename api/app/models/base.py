from datetime import UTC, datetime

from pydantic import field_serializer
from sqlmodel import SQLModel


def ahora_utc() -> datetime:
    return datetime.now(UTC)


class RespuestaConFecha(SQLModel):
    """
    Mixin para los modelos de salida.

    Garantiza que created_at viaje siempre con zona horaria: Postgres devuelve
    timestamptz con offset, pero SQLite no guarda la zona y devuelve una fecha
    naive. Sin esto, el navegador interpretaria esa fecha como hora local y la
    demo mostraria las horas corridas.
    """

    created_at: datetime

    @field_serializer("created_at")
    def _serializar_created_at(self, valor: datetime) -> str:
        return (valor if valor.tzinfo else valor.replace(tzinfo=UTC)).isoformat()

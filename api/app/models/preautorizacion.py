"""
Bitacora de dictamenes emitidos.

Es append-only y deliberadamente redundante: los escalares que se consultan
(veredicto, folio, montos) van en columnas, y el dictamen completo se guarda
como JSON para que la pantalla de casos pueda reconstruir la resolucion entera
sin depender de que el esquema no haya cambiado desde que se emitio.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel

from app.models.base import RespuestaConFecha, ahora_utc


class PreautorizacionBase(SQLModel):
    folio: str = Field(index=True, max_length=40)
    veredicto: str = Field(index=True, max_length=32)
    numero_poliza: str = Field(index=True, max_length=40)
    codigo_informe: str = Field(index=True, max_length=40)
    paciente: str = Field(max_length=160)
    cpt: str | None = Field(default=None, max_length=16)
    procedimiento: str | None = Field(default=None, max_length=160)
    monto_cotizado: float = 0.0
    cubierto_aseguradora: float = 0.0
    a_cargo_paciente: float = 0.0
    ms_total: int = 0
    origen_datos: str = Field(default="demo", max_length=16)
    notion_url: str | None = Field(default=None, max_length=500)


class Preautorizacion(PreautorizacionBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    # El dictamen entero, tal como se transmitio al navegador.
    dictamen: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=ahora_utc, sa_type=DateTime(timezone=True))


class PreautorizacionPublic(PreautorizacionBase, RespuestaConFecha):
    id: int
    dictamen: dict[str, Any] = {}

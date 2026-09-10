"""
Extractores de propiedades de Notion.

La API de Notion devuelve cada tipo de columna con una forma distinta y anidada
(`{"Cedula": {"type": "rich_text", "rich_text": [{"plain_text": "8-812-2043"}]}}`).
Estas funciones aplanan eso.

Todas son tolerantes a proposito: si la columna no existe, viene vacia o llega
con un tipo que no se esperaba, devuelven el valor por defecto y NUNCA lanzan.
Un evaluador que duplique estas bases en su propio Notion va a renombrar alguna
columna, y eso tiene que degradar el dato, no tumbar la peticion.
"""

from datetime import date
from typing import Any


def _prop(props: dict[str, Any], nombre: str) -> dict[str, Any]:
    valor = props.get(nombre)
    return valor if isinstance(valor, dict) else {}


def texto(props: dict[str, Any], nombre: str, defecto: str = "") -> str:
    """Sirve para `title` y para `rich_text`: los dos son listas de fragmentos."""
    prop = _prop(props, nombre)
    fragmentos = prop.get("title") or prop.get("rich_text") or []
    if not isinstance(fragmentos, list):
        return defecto
    unido = "".join(f.get("plain_text", "") for f in fragmentos if isinstance(f, dict)).strip()
    return unido or defecto


def numero(props: dict[str, Any], nombre: str, defecto: float = 0.0) -> float:
    prop = _prop(props, nombre)
    valor = prop.get("number")
    if isinstance(valor, int | float):
        return float(valor)
    # Una formula tambien puede dar un numero.
    formula = prop.get("formula")
    if isinstance(formula, dict) and isinstance(formula.get("number"), int | float):
        return float(formula["number"])
    return defecto


def entero(props: dict[str, Any], nombre: str, defecto: int = 0) -> int:
    return int(numero(props, nombre, float(defecto)))


def opcion(props: dict[str, Any], nombre: str, defecto: str = "") -> str:
    """`select` y `status` comparten forma: un objeto con `name`."""
    prop = _prop(props, nombre)
    elegido = prop.get("select") or prop.get("status")
    if isinstance(elegido, dict) and elegido.get("name"):
        return str(elegido["name"]).strip()
    return defecto


def opciones(props: dict[str, Any], nombre: str) -> list[str]:
    prop = _prop(props, nombre)
    valores = prop.get("multi_select")
    if not isinstance(valores, list):
        return []
    return [str(v["name"]).strip() for v in valores if isinstance(v, dict) and v.get("name")]


def fecha(props: dict[str, Any], nombre: str, defecto: date | None = None) -> date | None:
    prop = _prop(props, nombre)
    valor = prop.get("date")
    if not isinstance(valor, dict):
        return defecto
    inicio = valor.get("start")
    if not isinstance(inicio, str) or not inicio:
        return defecto
    try:
        # `start` puede venir como "2026-09-10" o con hora y zona.
        return date.fromisoformat(inicio[:10])
    except ValueError:
        return defecto


def marca(props: dict[str, Any], nombre: str, defecto: bool = False) -> bool:
    prop = _prop(props, nombre)
    valor = prop.get("checkbox")
    return valor if isinstance(valor, bool) else defecto


def lista_separada(props: dict[str, Any], nombre: str, sep: str = ";") -> list[str]:
    """Para listas de frases, que no caben bien en un `multi_select`."""
    crudo = texto(props, nombre)
    return [parte.strip() for parte in crudo.split(sep) if parte.strip()]

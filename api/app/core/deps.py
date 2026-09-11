from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlmodel import Session

from app.db.session import get_session
from app.repositorios.fabrica import NotionNoConfigurado, obtener_repositorio_escritura
from app.repositorios.notion import NotionRepositorio

SessionDep = Annotated[Session, Depends(get_session)]


def exigir_repositorio_escritura() -> NotionRepositorio:
    """
    Puerta de entrada de toda escritura.

    Falla ANTES de validar nada y antes de gastar un viaje a la red, y el 503
    explica que la lectura sigue en pie: quien lo lea tiene que entender que la
    aplicacion no esta rota, sino que le falta un permiso en Notion.
    """
    try:
        return obtener_repositorio_escritura()
    except NotionNoConfigurado as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error


EscrituraDep = Annotated[NotionRepositorio, Depends(exigir_repositorio_escritura)]

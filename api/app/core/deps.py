from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core.security import decode_token
from app.db.session import get_session
from app.models import User

SessionDep = Annotated[Session, Depends(get_session)]

# auto_error=False para devolver nosotros el 401 con un mensaje entendible.
_bearer = HTTPBearer(
    auto_error=False,
    description="Pega el access_token que devuelve /api/auth/login",
)


def get_current_user(
    session: SessionDep,
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credenciales is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Falta el token de acceso",
            {"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credenciales.credentials)
    except jwt.ExpiredSignatureError as error:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "La sesion expiro, vuelve a iniciar sesion"
        ) from error
    except jwt.PyJWTError as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido") from error

    subject = str(payload.get("sub", ""))
    usuario = session.get(User, int(subject)) if subject.isdigit() else None
    if usuario is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "El usuario del token ya no existe")

    return usuario


CurrentUser = Annotated[User, Depends(get_current_user)]

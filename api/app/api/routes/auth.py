from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.core.deps import CurrentUser, SessionDep
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Token, User, UserCreate, UserLogin, UserPublic

router = APIRouter(prefix="/auth", tags=["autenticacion"])

# Hash de descarte: si el correo no existe verificamos contra este para que el
# tiempo de respuesta no delate que usuarios estan registrados.
_HASH_DESCARTE = hash_password("no-existe-este-usuario")


@router.post(
    "/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Crear cuenta y recibir el token",
)
def register(datos: UserCreate, session: SessionDep) -> Token:
    ya_existe = session.exec(select(User).where(User.email == datos.email)).first()
    if ya_existe is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe una cuenta con ese correo")

    usuario = User(
        email=datos.email,
        full_name=datos.full_name,
        hashed_password=hash_password(datos.password),
    )
    session.add(usuario)
    session.commit()
    session.refresh(usuario)

    return Token(access_token=create_access_token(usuario.id))


@router.post("/login", response_model=Token, summary="Iniciar sesion")
def login(datos: UserLogin, session: SessionDep) -> Token:
    usuario = session.exec(select(User).where(User.email == datos.email)).first()

    if usuario is None:
        verify_password(datos.password, _HASH_DESCARTE)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Correo o contrasena incorrectos")

    if not verify_password(datos.password, usuario.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Correo o contrasena incorrectos")

    return Token(access_token=create_access_token(usuario.id))


@router.get("/me", response_model=UserPublic, summary="Usuario de la sesion actual")
def me(usuario: CurrentUser) -> User:
    return usuario

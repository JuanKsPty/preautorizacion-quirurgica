from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db.session import get_session
from app.main import app


@pytest.fixture(name="session")
def session_fixture() -> Generator[Session]:
    """
    SQLite en memoria, una base limpia por test. Asi la suite corre sin Docker
    ni Postgres: util en el CI y para cualquiera que solo clone el repo.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient]:
    # Sin el context manager no se ejecuta el lifespan, que intentaria crear
    # las tablas en la base real. La sesion se inyecta sobreescrita.
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(name="auth")
def auth_fixture(client: TestClient) -> dict[str, str]:
    """Registra un usuario y devuelve el header Authorization listo para usar."""
    respuesta = client.post(
        "/api/auth/register",
        json={"email": "tester@demo.com", "password": "password123", "full_name": "Tester"},
    )
    assert respuesta.status_code == 201, respuesta.text
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}

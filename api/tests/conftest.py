from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db.session import get_session
from app.main import app
from app.repositorios.demo import RepositorioDemo


@pytest.fixture(name="session")
def session_fixture() -> Generator[Session]:
    """
    SQLite en memoria, una base limpia por prueba. Asi la suite corre sin Docker
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


@pytest.fixture(name="repositorio")
def repositorio_fixture() -> RepositorioDemo:
    return RepositorioDemo()

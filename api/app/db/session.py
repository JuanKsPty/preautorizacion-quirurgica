from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings


def _engine_kwargs() -> dict:
    if settings.database_kind == "sqlite":
        # SQLite necesita esto para que FastAPI pueda usar la conexion en
        # distintos hilos del threadpool.
        return {"connect_args": {"check_same_thread": False}}
    # pool_pre_ping evita el clasico "server closed the connection" cuando
    # Postgres estuvo un rato sin trafico.
    return {"pool_pre_ping": True}


engine = create_engine(settings.database_url, echo=False, **_engine_kwargs())


def create_db_and_tables() -> None:
    """Crea las tablas que falten. Solo para desarrollo: en produccion, Alembic."""
    import app.models  # noqa: F401  (registra los modelos en SQLModel.metadata)

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session]:
    with Session(engine) as session:
        yield session

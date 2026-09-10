from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuracion de la API. Se lee del .env de la RAIZ del proyecto
    (../.env cuando se corre desde api/) y, si existe, de un api/.env que
    tiene prioridad. En Docker las variables llegan del entorno.
    """

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Hackathon Starter API"
    app_version: str = "1.0.0"
    app_env: str = "dev"

    # ---- Base de datos -------------------------------------------------
    # Por defecto, el Postgres que levanta docker compose. Dentro de la red de
    # compose el host es "db" y la propia compose lo inyecta; este valor es el
    # que usan los comandos que se corren desde la maquina (Alembic, seed).
    # Si falta el .env preferimos que /api/health diga "sin conexion" antes que
    # caer en un SQLite silencioso que nadie pidio.
    database_url: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/app"
    # En dev creamos las tablas al arrancar. Ponlo en false cuando empieces
    # a usar migraciones de Alembic, para que no compitan entre si.
    auto_create_tables: bool = True

    # ---- Seguridad -----------------------------------------------------
    jwt_secret: str = "cambia-esto-por-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # ---- IA ------------------------------------------------------------
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"
    anthropic_max_tokens: int = 1024

    # ---- CORS ----------------------------------------------------------
    # Se deja como str y no como list[str] a proposito: pydantic-settings
    # intenta parsear las listas como JSON y "a,b" haria estallar el arranque.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origen.strip() for origen in self.cors_origins.split(",") if origen.strip()]

    @property
    def ai_enabled(self) -> bool:
        return bool(self.anthropic_api_key.strip())

    @property
    def database_kind(self) -> str:
        return "sqlite" if self.database_url.startswith("sqlite") else "postgresql"

    @property
    def is_dev(self) -> bool:
        return self.app_env.lower() in {"dev", "development", "local"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

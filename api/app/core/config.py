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

    app_name: str = "API de Pre-Autorizacion Quirurgica"
    app_version: str = "1.0.0"
    app_env: str = "dev"

    # ---- Base de datos -------------------------------------------------
    # Solo guarda la bitacora de dictamenes emitidos. La fuente de verdad de
    # polizas e informes es Notion (o los datos de demostracion).
    database_url: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/app"
    auto_create_tables: bool = True

    # ---- IA ------------------------------------------------------------
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5"
    # Un turno con uso de herramientas y razonamiento necesita espacio: con
    # 1024 el modelo se corta a mitad de un tool_use y el bucle se rompe.
    anthropic_max_tokens: int = 8192
    # low | medium | high | xhigh | max. En "medium" el agente responde en
    # pocos segundos, que es lo que importa en una demo en vivo: toda la
    # aritmetica dificil ya la hacen las herramientas deterministas.
    anthropic_effort: str = "medium"
    # La extraccion del formulario es transcripcion, no criterio: no hay
    # aritmetica ni veredicto. En "low" responde en 3-5 s en vez de 15, y un
    # prerrelleno de 15 segundos se abandona antes de que termine.
    anthropic_effort_extraccion: str = "low"
    # Tope de una extraccion. El defecto del SDK son 10 minutos con 2 reintentos:
    # sin esto, una llamada lenta deja el formulario colgado media hora.
    extraccion_timeout_segundos: float = 25.0

    # ---- Agente --------------------------------------------------------
    agente_max_iteraciones: int = 8
    # Techo absoluto de una evaluacion. Sin esto, el timeout por defecto del
    # SDK (10 min y 2 reintentos) puede dejar el stream colgado media hora.
    agente_timeout_segundos: int = 150
    # Cada cuanto se manda un latido para que ningun proxy corte por inactividad.
    sse_latido_segundos: int = 15

    # ---- Notion --------------------------------------------------------
    notion_token: str = ""
    notion_db_polizas: str = ""
    notion_db_informes: str = ""
    notion_db_procedimientos: str = ""
    notion_db_preautorizaciones: str = ""
    notion_version: str = "2025-09-03"

    # ---- CORS ----------------------------------------------------------
    # Se deja como str y no como list[str] a proposito: pydantic-settings
    # intenta parsear las listas como JSON y "a,b" haria estallar el arranque.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origen.strip() for origen in self.cors_origins.split(",") if origen.strip()]

    @property
    def ia_habilitada(self) -> bool:
        return bool(self.anthropic_api_key.strip())

    @property
    def notion_habilitado(self) -> bool:
        """Notion solo se usa si hay token Y estan los cuatro identificadores."""
        return bool(self.notion_token.strip()) and all(
            [
                self.notion_db_polizas.strip(),
                self.notion_db_informes.strip(),
                self.notion_db_procedimientos.strip(),
            ]
        )

    @property
    def origen_datos(self) -> str:
        return "notion" if self.notion_habilitado else "demo"

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

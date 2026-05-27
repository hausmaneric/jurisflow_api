import json
import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv() -> None:
        return None


@dataclass
class AppConfig:
    apiName: str = "JurisFlow API"
    apiVersion: str = "1.0.0"
    apiInfo: str = "API SaaS juridica multiempresa"
    databaseUrl: str = ""
    dbHost: str = "localhost"
    dbPort: int = 5432
    dbName: str = "jurisflow"
    dbUser: str = "postgres"
    dbPassword: str = ""
    dbSslMode: str = "prefer"
    secretKey: str = "change-me"
    setupKey: str = ""
    jwtExpiresHours: int = 12


appConfig = AppConfig()


def load_runtime_config() -> None:
    load_dotenv()
    config_path = Path(__file__).resolve().parents[3] / "_config.server.json"
    runtime_data = {}

    if config_path.exists():
        runtime_data = json.loads(config_path.read_text(encoding="utf-8") or "{}")

    env_map = {
        "JURISFLOW_API_NAME": os.getenv("JURISFLOW_API_NAME"),
        "JURISFLOW_API_VERSION": os.getenv("JURISFLOW_API_VERSION"),
        "JURISFLOW_DATABASE_URL": os.getenv("JURISFLOW_DATABASE_URL"),
        "JURISFLOW_DB_HOST": os.getenv("JURISFLOW_DB_HOST"),
        "JURISFLOW_DB_PORT": os.getenv("JURISFLOW_DB_PORT"),
        "JURISFLOW_DB_NAME": os.getenv("JURISFLOW_DB_NAME"),
        "JURISFLOW_DB_USER": os.getenv("JURISFLOW_DB_USER"),
        "JURISFLOW_DB_PASSWORD": os.getenv("JURISFLOW_DB_PASSWORD"),
        "JURISFLOW_DB_SSLMODE": os.getenv("JURISFLOW_DB_SSLMODE"),
        "JURISFLOW_SECRET_KEY": os.getenv("JURISFLOW_SECRET_KEY"),
        "JURISFLOW_SETUP_KEY": os.getenv("JURISFLOW_SETUP_KEY"),
        "JURISFLOW_JWT_EXPIRES_HOURS": os.getenv("JURISFLOW_JWT_EXPIRES_HOURS"),
    }

    for key, value in env_map.items():
        if value not in (None, ""):
            runtime_data[key] = value

    appConfig.apiName = runtime_data.get("JURISFLOW_API_NAME", appConfig.apiName)
    appConfig.apiVersion = runtime_data.get("JURISFLOW_API_VERSION", appConfig.apiVersion)
    appConfig.databaseUrl = runtime_data.get("JURISFLOW_DATABASE_URL", appConfig.databaseUrl)
    appConfig.dbHost = runtime_data.get("JURISFLOW_DB_HOST", appConfig.dbHost)
    appConfig.dbPort = int(runtime_data.get("JURISFLOW_DB_PORT", appConfig.dbPort))
    appConfig.dbName = runtime_data.get("JURISFLOW_DB_NAME", appConfig.dbName)
    appConfig.dbUser = runtime_data.get("JURISFLOW_DB_USER", appConfig.dbUser)
    appConfig.dbPassword = runtime_data.get("JURISFLOW_DB_PASSWORD", appConfig.dbPassword)
    appConfig.dbSslMode = runtime_data.get("JURISFLOW_DB_SSLMODE", appConfig.dbSslMode)
    appConfig.secretKey = runtime_data.get("JURISFLOW_SECRET_KEY", appConfig.secretKey)
    appConfig.setupKey = runtime_data.get("JURISFLOW_SETUP_KEY", appConfig.setupKey)
    appConfig.jwtExpiresHours = int(runtime_data.get("JURISFLOW_JWT_EXPIRES_HOURS", appConfig.jwtExpiresHours))

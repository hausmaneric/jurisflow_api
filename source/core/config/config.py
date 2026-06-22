import json
import os
from dataclasses import dataclass
from pathlib import Path

DATAJUD_PUBLIC_API_KEY = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

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
    publicBaseUrl: str = ""
    storageMode: str = "local"
    storageRoot: str = "storage"
    storagePublicBaseUrl: str = ""
    s3EndpointUrl: str = ""
    s3Region: str = "auto"
    s3Bucket: str = ""
    s3AccessKeyId: str = ""
    s3SecretAccessKey: str = ""
    s3PresignExpiresSeconds: int = 3600
    datajudApiKey: str = DATAJUD_PUBLIC_API_KEY
    datajudBaseUrl: str = "https://api-publica.datajud.cnj.jus.br"
    serverCourtConnectorUrl: str = ""
    serverCourtConnectorToken: str = ""
    localCourtBridgeUrl: str = "http://127.0.0.1:8765/tribunal-sync"
    transcriptionProvider: str = "manual"
    whisperWorkerUrl: str = ""
    whisperWorkerToken: str = ""
    webBaseUrl: str = ""
    googleClientId: str = ""
    googleClientSecret: str = ""
    googleRedirectUri: str = ""


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
        "JURISFLOW_PUBLIC_BASE_URL": os.getenv("JURISFLOW_PUBLIC_BASE_URL"),
        "JURISFLOW_STORAGE_MODE": os.getenv("JURISFLOW_STORAGE_MODE"),
        "JURISFLOW_STORAGE_ROOT": os.getenv("JURISFLOW_STORAGE_ROOT"),
        "JURISFLOW_STORAGE_PUBLIC_BASE_URL": os.getenv("JURISFLOW_STORAGE_PUBLIC_BASE_URL"),
        "JURISFLOW_S3_ENDPOINT_URL": os.getenv("JURISFLOW_S3_ENDPOINT_URL"),
        "JURISFLOW_S3_REGION": os.getenv("JURISFLOW_S3_REGION"),
        "JURISFLOW_S3_BUCKET": os.getenv("JURISFLOW_S3_BUCKET"),
        "JURISFLOW_S3_ACCESS_KEY_ID": os.getenv("JURISFLOW_S3_ACCESS_KEY_ID"),
        "JURISFLOW_S3_SECRET_ACCESS_KEY": os.getenv("JURISFLOW_S3_SECRET_ACCESS_KEY"),
        "JURISFLOW_S3_PRESIGN_EXPIRES_SECONDS": os.getenv("JURISFLOW_S3_PRESIGN_EXPIRES_SECONDS"),
        "JURISFLOW_DATAJUD_API_KEY": os.getenv("JURISFLOW_DATAJUD_API_KEY"),
        "JURISFLOW_DATAJUD_BASE_URL": os.getenv("JURISFLOW_DATAJUD_BASE_URL"),
        "JURISFLOW_SERVER_COURT_CONNECTOR_URL": os.getenv("JURISFLOW_SERVER_COURT_CONNECTOR_URL"),
        "JURISFLOW_SERVER_COURT_CONNECTOR_TOKEN": os.getenv("JURISFLOW_SERVER_COURT_CONNECTOR_TOKEN"),
        "JURISFLOW_LOCAL_COURT_BRIDGE_URL": os.getenv("JURISFLOW_LOCAL_COURT_BRIDGE_URL"),
        "JURISFLOW_TRANSCRIPTION_PROVIDER": os.getenv("JURISFLOW_TRANSCRIPTION_PROVIDER"),
        "JURISFLOW_WHISPER_WORKER_URL": os.getenv("JURISFLOW_WHISPER_WORKER_URL"),
        "JURISFLOW_WHISPER_WORKER_TOKEN": os.getenv("JURISFLOW_WHISPER_WORKER_TOKEN"),
        "JURISFLOW_WEB_BASE_URL": os.getenv("JURISFLOW_WEB_BASE_URL"),
        "JURISFLOW_GOOGLE_CLIENT_ID": os.getenv("JURISFLOW_GOOGLE_CLIENT_ID"),
        "JURISFLOW_GOOGLE_CLIENT_SECRET": os.getenv("JURISFLOW_GOOGLE_CLIENT_SECRET"),
        "JURISFLOW_GOOGLE_REDIRECT_URI": os.getenv("JURISFLOW_GOOGLE_REDIRECT_URI"),
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
    appConfig.publicBaseUrl = runtime_data.get("JURISFLOW_PUBLIC_BASE_URL", appConfig.publicBaseUrl)
    appConfig.storageMode = runtime_data.get("JURISFLOW_STORAGE_MODE", appConfig.storageMode)
    appConfig.storageRoot = runtime_data.get("JURISFLOW_STORAGE_ROOT", appConfig.storageRoot)
    appConfig.storagePublicBaseUrl = runtime_data.get("JURISFLOW_STORAGE_PUBLIC_BASE_URL", appConfig.storagePublicBaseUrl)
    appConfig.s3EndpointUrl = runtime_data.get("JURISFLOW_S3_ENDPOINT_URL", appConfig.s3EndpointUrl)
    appConfig.s3Region = runtime_data.get("JURISFLOW_S3_REGION", appConfig.s3Region)
    appConfig.s3Bucket = runtime_data.get("JURISFLOW_S3_BUCKET", appConfig.s3Bucket)
    appConfig.s3AccessKeyId = runtime_data.get("JURISFLOW_S3_ACCESS_KEY_ID", appConfig.s3AccessKeyId)
    appConfig.s3SecretAccessKey = runtime_data.get("JURISFLOW_S3_SECRET_ACCESS_KEY", appConfig.s3SecretAccessKey)
    appConfig.s3PresignExpiresSeconds = int(runtime_data.get("JURISFLOW_S3_PRESIGN_EXPIRES_SECONDS", appConfig.s3PresignExpiresSeconds))
    appConfig.datajudApiKey = runtime_data.get("JURISFLOW_DATAJUD_API_KEY", appConfig.datajudApiKey)
    appConfig.datajudBaseUrl = runtime_data.get("JURISFLOW_DATAJUD_BASE_URL", appConfig.datajudBaseUrl)
    appConfig.serverCourtConnectorUrl = runtime_data.get("JURISFLOW_SERVER_COURT_CONNECTOR_URL", appConfig.serverCourtConnectorUrl)
    appConfig.serverCourtConnectorToken = runtime_data.get("JURISFLOW_SERVER_COURT_CONNECTOR_TOKEN", appConfig.serverCourtConnectorToken)
    appConfig.localCourtBridgeUrl = runtime_data.get("JURISFLOW_LOCAL_COURT_BRIDGE_URL", appConfig.localCourtBridgeUrl)
    appConfig.transcriptionProvider = runtime_data.get("JURISFLOW_TRANSCRIPTION_PROVIDER", appConfig.transcriptionProvider)
    appConfig.whisperWorkerUrl = runtime_data.get("JURISFLOW_WHISPER_WORKER_URL", appConfig.whisperWorkerUrl)
    appConfig.whisperWorkerToken = runtime_data.get("JURISFLOW_WHISPER_WORKER_TOKEN", appConfig.whisperWorkerToken)
    appConfig.webBaseUrl = runtime_data.get("JURISFLOW_WEB_BASE_URL", appConfig.webBaseUrl)
    appConfig.googleClientId = runtime_data.get("JURISFLOW_GOOGLE_CLIENT_ID", appConfig.googleClientId)
    appConfig.googleClientSecret = runtime_data.get("JURISFLOW_GOOGLE_CLIENT_SECRET", appConfig.googleClientSecret)
    appConfig.googleRedirectUri = runtime_data.get("JURISFLOW_GOOGLE_REDIRECT_URI", appConfig.googleRedirectUri)

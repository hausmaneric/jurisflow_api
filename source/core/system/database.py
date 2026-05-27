from urllib.parse import urlparse

try:
    import psycopg2
    from psycopg2 import pool
    from psycopg2.extras import RealDictCursor
except ImportError:  # pragma: no cover
    psycopg2 = None
    pool = None
    RealDictCursor = None

from source.core.config.config import appConfig
from source.core.system.utils import NXResult


def build_connection_string() -> str:
    if appConfig.databaseUrl:
        return appConfig.databaseUrl

    return (
        f"host={appConfig.dbHost} "
        f"port={appConfig.dbPort} "
        f"dbname={appConfig.dbName} "
        f"user={appConfig.dbUser} "
        f"password={appConfig.dbPassword} "
        f"sslmode={appConfig.dbSslMode}"
    )


def validate_master_database_config() -> dict:
    issues = []
    mode = "database_url" if appConfig.databaseUrl else "discrete"

    if appConfig.databaseUrl:
        parsed = urlparse(appConfig.databaseUrl)
        if parsed.scheme not in ("postgres", "postgresql"):
            issues.append("JURISFLOW_DATABASE_URL parece invalida")
    else:
        required_map = {
            "JURISFLOW_DB_HOST": appConfig.dbHost,
            "JURISFLOW_DB_PORT": appConfig.dbPort,
            "JURISFLOW_DB_NAME": appConfig.dbName,
            "JURISFLOW_DB_USER": appConfig.dbUser,
            "JURISFLOW_DB_PASSWORD": appConfig.dbPassword,
        }
        for key, value in required_map.items():
            if value in (None, "", 0):
                issues.append(f"{key} nao configurado")

    return {"valid": len(issues) == 0, "mode": mode, "issues": issues}


class NXDatabaseConnection:
    _pool_registry: dict[str, object] = {}

    def __init__(self) -> None:
        self.conn_nx = None
        self.xp_nx = None
        self.activate = False
        self._pool_key = None

    def stop(self) -> None:
        if self.activate and self.conn_nx:
            try:
                self._pool_registry[self._pool_key].putconn(self.conn_nx, close=bool(getattr(self.conn_nx, "closed", 0)))
            except Exception:
                try:
                    self.conn_nx.close()
                except Exception:
                    pass
        self.conn_nx = None
        self.xp_nx = None
        self.activate = False
        self._pool_key = None

    @classmethod
    def _get_pool(cls, connection_string: str):
        if pool is None or RealDictCursor is None:
            raise RuntimeError("psycopg2-binary nao instalado")
        if connection_string not in cls._pool_registry:
            cls._pool_registry[connection_string] = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=connection_string,
                cursor_factory=RealDictCursor,
            )
        return cls._pool_registry[connection_string]

    def active(self) -> NXResult:
        result = NXResult()
        try:
            if psycopg2 is None:
                raise RuntimeError("psycopg2-binary nao instalado")
            connection_string = build_connection_string()
            conn_pool = self._get_pool(connection_string)
            self.conn_nx = conn_pool.getconn()
            self.xp_nx = self.conn_nx.cursor(cursor_factory=RealDictCursor)
            self._pool_key = connection_string
            self.activate = True
            result.status = True
        except Exception as exc:
            result.make_error(0, "Falha na conexao com a base de dados", str(exc))
        return result


def master_database_ping() -> NXResult:
    result = NXResult()
    validation = validate_master_database_config()
    if validation["valid"] is False:
        result.make_error(0, "Configuracao do banco principal invalida", "; ".join(validation["issues"]))
        result.data = validation
        return result

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute("SELECT 1 AS ok")
        row = nx.xp_nx.fetchone()
        result.status = True
        result.message = "Banco principal acessivel"
        result.data = dict(row or {"ok": 1})
    except Exception as exc:
        result.make_error(0, "Falha no ping do banco principal", str(exc))
    finally:
        nx.stop()

    return result

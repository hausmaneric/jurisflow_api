import os
from pathlib import Path

from source.core.config.config import appConfig
from source.core.system.database import NXDatabaseConnection


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _read_sql(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def auto_migrate_database() -> None:
    """Apply the base schema and pending SQL migrations at application boot.

    Railway can provision an empty PostgreSQL database for a fresh service. The
    API needs its tables before the first request, so this runner is purposely
    idempotent and relies on the schema/migrations using IF NOT EXISTS patterns.
    """

    auto_migrate = os.getenv("JURISFLOW_AUTO_MIGRATE")
    if auto_migrate and auto_migrate.strip().lower() in {"0", "false", "no", "off"}:
        return

    if not auto_migrate and not appConfig.databaseUrl:
        # Avoid breaking local imports/tests that do not configure PostgreSQL.
        # Railway should set JURISFLOW_DATABASE_URL, which enables this by default.
        return

    root = _project_root()
    schema_path = root / "database" / "schema.sql"
    migrations_dir = root / "database" / "migrations"

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        raise RuntimeError(opened.message or opened.detail or "Falha ao conectar ao banco para migrations")

    try:
        if schema_path.exists():
            schema_sql = _read_sql(schema_path)
            if schema_sql:
                nx.xp_nx.execute(schema_sql)

        nx.xp_nx.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )

        if migrations_dir.exists():
            for migration_path in sorted(migrations_dir.glob("*.sql")):
                nx.xp_nx.execute("SELECT 1 FROM schema_migrations WHERE name = %s", (migration_path.name,))
                if nx.xp_nx.fetchone():
                    continue

                migration_sql = _read_sql(migration_path)
                if migration_sql:
                    nx.xp_nx.execute(migration_sql)
                nx.xp_nx.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (migration_path.name,))

        nx.conn_nx.commit()
    except Exception:
        nx.conn_nx.rollback()
        raise
    finally:
        nx.stop()

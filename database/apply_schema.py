import os
from pathlib import Path

try:
    import psycopg2
except ImportError as exc:  # pragma: no cover
    raise SystemExit(f"psycopg2-binary nao instalado: {exc}")


def main() -> int:
    database_url = os.getenv("JURISFLOW_DATABASE_URL")
    if not database_url:
        raise SystemExit("Defina JURISFLOW_DATABASE_URL antes de aplicar o schema.")

    schema_path = Path(__file__).with_name("schema.sql")
    schema_sql = schema_path.read_text(encoding="utf-8")

    conn = psycopg2.connect(database_url)
    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(schema_sql)
        print("Schema aplicado com sucesso.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

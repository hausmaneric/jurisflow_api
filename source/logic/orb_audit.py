import json

from source.core.system.database import NXDatabaseConnection


def register_audit_log(company_id: str, user_id: str | None, entity: str, entity_id: str | None, action: str, old_data=None, new_data=None) -> None:
    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return

    try:
        nx.xp_nx.execute(
            """
            INSERT INTO audit_logs (company_id, user_id, entity, entity_id, action, old_data, new_data)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
            """,
            (
                company_id,
                user_id,
                entity,
                entity_id,
                action,
                json.dumps(old_data) if old_data is not None else None,
                json.dumps(new_data) if new_data is not None else None,
            ),
        )
        nx.conn_nx.commit()
    except Exception:
        nx.conn_nx.rollback()
    finally:
        nx.stop()

from source.core.system.database import NXDatabaseConnection
from source.core.system.utils import NXResult
from source.data.sql.sql_reports import SQL_TIMELINE


def operational_summary(session_payload: dict) -> NXResult:
    r = NXResult()
    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        company_id = session_payload["company_id"]
        metrics = {}
        queries = {
            "clients": "SELECT COUNT(*) AS total FROM clients WHERE company_id = %s AND deleted_at IS NULL",
            "lawyers": "SELECT COUNT(*) AS total FROM lawyers WHERE company_id = %s AND deleted_at IS NULL",
            "cases_open": "SELECT COUNT(*) AS total FROM cases WHERE company_id = %s AND deleted_at IS NULL AND status = 'open'",
            "appointments_upcoming": "SELECT COUNT(*) AS total FROM appointments WHERE company_id = %s AND deleted_at IS NULL AND start_at >= NOW()",
            "tasks_open": "SELECT COUNT(*) AS total FROM tasks WHERE company_id = %s AND deleted_at IS NULL AND status IN ('open', 'pending')",
            "documents": "SELECT COUNT(*) AS total FROM documents WHERE company_id = %s AND deleted_at IS NULL",
            "notifications_pending": "SELECT COUNT(*) AS total FROM notifications WHERE company_id = %s AND status = 'pending'",
        }
        for key, sql in queries.items():
            nx.xp_nx.execute(sql, (company_id,))
            metrics[key] = nx.xp_nx.fetchone()["total"]

        r.status = True
        r.message = "Resumo operacional carregado com sucesso"
        r.data = metrics
    except Exception as exc:
        r.make_error(0, "Erro ao carregar resumo operacional", str(exc))
    finally:
        nx.stop()

    return r


def operational_timeline(session_payload: dict) -> NXResult:
    r = NXResult()
    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        company_id = session_payload["company_id"]
        nx.xp_nx.execute(SQL_TIMELINE, (company_id, company_id, company_id))
        rows = nx.xp_nx.fetchall()
        r.status = True
        r.message = "Timeline operacional carregada com sucesso"
        r.data = [dict(row) for row in rows]
    except Exception as exc:
        r.make_error(0, "Erro ao carregar timeline operacional", str(exc))
    finally:
        nx.stop()

    return r

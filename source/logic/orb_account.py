from source.core.system.database import NXDatabaseConnection
from source.core.system.utils import NXResult
from source.logic.orb_audit import register_audit_log


def get_current_user_profile(session_payload: dict) -> NXResult:
    r = NXResult()
    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            """
            SELECT u.id, u.company_id, u.role_id, u.name, u.email, u.phone, u.status, u.active, u.last_login_at,
                   c.code AS company_code, c.name AS company_name,
                   ro.name AS role_name
            FROM users u
            JOIN companies c ON c.id = u.company_id
            LEFT JOIN roles ro ON ro.id = u.role_id
            WHERE u.id = %s AND u.company_id = %s AND u.deleted_at IS NULL
            """,
            (session_payload["user_id"], session_payload["company_id"]),
        )
        row = nx.xp_nx.fetchone()
        if not row:
            r.make_error(404, "Usuario nao localizado")
        else:
            r.status = True
            r.message = "Perfil carregado com sucesso"
            r.data = dict(row)
    except Exception as exc:
        r.make_error(0, "Erro ao carregar perfil", str(exc))
    finally:
        nx.stop()

    return r


def get_company_settings(session_payload: dict) -> NXResult:
    r = NXResult()
    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            """
            SELECT cs.id, cs.company_id, cs.billing_email, cs.timezone, cs.locale, cs.storage_limit_mb, cs.storage_used_mb, cs.settings,
                   c.code, c.name, c.document, c.email, c.phone, c.logo_url, c.status, c.plan_id
            FROM company_settings cs
            JOIN companies c ON c.id = cs.company_id
            WHERE cs.company_id = %s AND c.deleted_at IS NULL
            """,
            (session_payload["company_id"],),
        )
        row = nx.xp_nx.fetchone()
        if not row:
            r.make_error(404, "Configuracoes da empresa nao localizadas")
        else:
            r.status = True
            r.message = "Configuracoes da empresa carregadas com sucesso"
            r.data = dict(row)
    except Exception as exc:
        r.make_error(0, "Erro ao carregar configuracoes da empresa", str(exc))
    finally:
        nx.stop()

    return r


def update_company_settings(session_payload: dict, payload: dict) -> NXResult:
    r = NXResult()
    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            """
            UPDATE company_settings
            SET billing_email = COALESCE(%s, billing_email),
                timezone = COALESCE(%s, timezone),
                locale = COALESCE(%s, locale),
                storage_limit_mb = COALESCE(%s, storage_limit_mb),
                settings = COALESCE(%s::jsonb, settings),
                updated_at = NOW()
            WHERE company_id = %s
            RETURNING id
            """,
            (
                payload.get("billing_email"),
                payload.get("timezone"),
                payload.get("locale"),
                payload.get("storage_limit_mb"),
                payload.get("settings"),
                session_payload["company_id"],
            ),
        )
        row = nx.xp_nx.fetchone()
        if not row:
            nx.conn_nx.rollback()
            r.make_error(404, "Configuracoes da empresa nao localizadas")
            return r

        if any(key in payload for key in ("name", "document", "email", "phone", "logo_url", "status")):
            nx.xp_nx.execute(
                """
                UPDATE companies
                SET name = COALESCE(%s, name),
                    document = COALESCE(%s, document),
                    email = COALESCE(%s, email),
                    phone = COALESCE(%s, phone),
                    logo_url = COALESCE(%s, logo_url),
                    status = COALESCE(%s, status),
                    updated_at = NOW()
                WHERE id = %s
                """,
                (
                    payload.get("name"),
                    payload.get("document"),
                    payload.get("email"),
                    payload.get("phone"),
                    payload.get("logo_url"),
                    payload.get("status"),
                    session_payload["company_id"],
                ),
            )

        nx.conn_nx.commit()
        register_audit_log(session_payload["company_id"], session_payload.get("user_id"), "company_settings", str(row["id"]), "update", None, payload)
        r.status = True
        r.message = "Configuracoes da empresa atualizadas com sucesso"
        r.data = {"id": str(row["id"])}
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao atualizar configuracoes da empresa", str(exc))
    finally:
        nx.stop()

    return r

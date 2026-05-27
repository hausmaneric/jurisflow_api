from source.core.config.config import appConfig
from source.core.system.database import NXDatabaseConnection
from source.core.system.security import hash_password
from source.core.system.utils import NXResult


def bootstrap_company(payload: dict, setup_key: str) -> NXResult:
    r = NXResult()
    if not appConfig.setupKey:
        r.make_error(0, "JURISFLOW_SETUP_KEY nao configurada")
        return r

    if setup_key != appConfig.setupKey:
        r.make_error(401, "Setup key invalida")
        return r

    required_fields = [
        "company_code",
        "company_name",
        "admin_name",
        "admin_email",
        "admin_password",
    ]
    missing = [field for field in required_fields if not payload.get(field)]
    if missing:
        r.make_error(0, f"Campos obrigatorios ausentes: {', '.join(missing)}")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            """
            INSERT INTO plans (name, description, max_users, max_cases, max_storage_mb, active)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            ("Plano Inicial", "Plano padrao do bootstrap inicial", 10, 300, 2048, True),
        )
        plan_row = nx.xp_nx.fetchone()
        if not plan_row:
            nx.xp_nx.execute("SELECT id FROM plans ORDER BY created_at ASC LIMIT 1")
            plan_row = nx.xp_nx.fetchone()

        nx.xp_nx.execute(
            """
            INSERT INTO companies (code, name, document, email, phone, status, plan_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                payload["company_code"],
                payload["company_name"],
                payload.get("company_document"),
                payload.get("company_email"),
                payload.get("company_phone"),
                "active",
                plan_row["id"],
            ),
        )
        company = nx.xp_nx.fetchone()

        nx.xp_nx.execute(
            """
            INSERT INTO roles (company_id, name, description, is_admin, active)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                company["id"],
                "Administrador",
                "Perfil administrativo inicial do escritorio",
                True,
                True,
            ),
        )
        role = nx.xp_nx.fetchone()

        nx.xp_nx.execute(
            """
            INSERT INTO users (company_id, role_id, name, email, password_hash, phone, status, active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                company["id"],
                role["id"],
                payload["admin_name"],
                payload["admin_email"],
                hash_password(payload["admin_password"]),
                payload.get("admin_phone"),
                "active",
                True,
            ),
        )
        user = nx.xp_nx.fetchone()

        nx.xp_nx.execute(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT %s, id
            FROM permissions
            ON CONFLICT DO NOTHING
            """,
            (role["id"],),
        )

        nx.xp_nx.execute(
            """
            INSERT INTO company_settings (company_id, billing_email, timezone, locale, storage_limit_mb, storage_used_mb, settings)
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
            """,
            (
                company["id"],
                payload.get("billing_email") or payload.get("company_email"),
                payload.get("timezone") or "America/Sao_Paulo",
                payload.get("locale") or "pt-BR",
                payload.get("storage_limit_mb") or 2048,
                0,
                "{}",
            ),
        )

        nx.conn_nx.commit()
        r.status = True
        r.message = "Bootstrap inicial concluido com sucesso"
        r.data = {
            "company_id": str(company["id"]),
            "role_id": str(role["id"]),
            "admin_user_id": str(user["id"]),
        }
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao executar bootstrap inicial", str(exc))
    finally:
        nx.stop()

    return r

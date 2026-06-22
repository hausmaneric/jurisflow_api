import json

from source.core.config.config import appConfig
from source.core.system.database import NXDatabaseConnection
from source.core.system.security import hash_password
from source.core.system.utils import NXResult


PLAN_CATALOG = {
    "starter": {
        "name": "Starter",
        "description": "Plano inicial para escritorios em estruturacao",
        "max_users": 2,
        "max_cases": 150,
        "max_storage_mb": 2048,
        "billing_cycle": "monthly",
        "monthly_price_brl": 79.90,
    },
    "pro": {
        "name": "Pro",
        "description": "Plano profissional para escritorios em crescimento",
        "max_users": 25,
        "max_cases": 1500,
        "max_storage_mb": 10240,
        "billing_cycle": "monthly",
        "monthly_price_brl": 149.90,
    },
    "enterprise": {
        "name": "Enterprise",
        "description": "Plano completo com automacoes, integracoes e API",
        "max_users": 250,
        "max_cases": 10000,
        "max_storage_mb": 51200,
        "billing_cycle": "monthly",
        "monthly_price_brl": 299.90,
    },
}


def _validate_signup_payload(payload: dict) -> list[str]:
    required_fields = [
        "company_code",
        "company_name",
        "admin_name",
        "admin_email",
        "admin_password",
    ]
    return [field for field in required_fields if not payload.get(field)]


def _normalize_plan_code(payload: dict) -> str:
    raw = (payload.get("plan_code") or payload.get("plan") or payload.get("plan_name") or "enterprise").strip().lower()
    aliases = {
        "plano inicial": "starter",
        "inicial": "starter",
        "professional": "pro",
        "profissional": "pro",
        "empresarial": "enterprise",
    }
    return aliases.get(raw, raw if raw in PLAN_CATALOG else "enterprise")


def _ensure_plan(nx: NXDatabaseConnection, plan_code: str) -> dict:
    plan = PLAN_CATALOG[plan_code]
    nx.xp_nx.execute("SELECT id, name, max_storage_mb FROM plans WHERE LOWER(name) = LOWER(%s) LIMIT 1", (plan["name"],))
    row = nx.xp_nx.fetchone()
    if row:
        nx.xp_nx.execute(
            """
            UPDATE plans
            SET description = %s,
                max_users = %s,
                max_cases = %s,
                max_storage_mb = %s,
                active = TRUE,
                updated_at = NOW()
            WHERE id = %s
            """,
            (plan["description"], plan["max_users"], plan["max_cases"], plan["max_storage_mb"], row["id"]),
        )
        return {**plan, "id": row["id"]}

    nx.xp_nx.execute(
        """
        INSERT INTO plans (name, description, max_users, max_cases, max_storage_mb, active)
        VALUES (%s, %s, %s, %s, %s, TRUE)
        RETURNING id
        """,
        (plan["name"], plan["description"], plan["max_users"], plan["max_cases"], plan["max_storage_mb"]),
    )
    created = nx.xp_nx.fetchone()
    return {**plan, "id": created["id"]}


def _provision_company(payload: dict, success_message: str) -> NXResult:
    r = NXResult()
    missing = _validate_signup_payload(payload)
    if missing:
        r.make_error(0, f"Campos obrigatorios ausentes: {', '.join(missing)}")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        plan_code = _normalize_plan_code(payload)
        plan_row = _ensure_plan(nx, plan_code)

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
                payload.get("storage_limit_mb") or plan_row["max_storage_mb"],
                0,
                json.dumps(
                    {
                        "office_oab": payload.get("office_oab") or "",
                        "office_address": payload.get("office_address") or "",
                        "office_number": payload.get("office_number") or "",
                        "office_complement": payload.get("office_complement") or "",
                        "office_city": payload.get("office_city") or "",
                        "office_state": payload.get("office_state") or "",
                        "office_postal_code": payload.get("office_postal_code") or "",
                    }
                ),
            ),
        )

        nx.xp_nx.execute(
            """
            INSERT INTO company_subscriptions (
                company_id,
                plan_id,
                status,
                billing_cycle,
                current_period_start,
                current_period_end,
                billing_data
            )
            VALUES (%s, %s, 'active', %s, NOW(), NOW() + INTERVAL '30 days', %s::jsonb)
            """,
            (
                company["id"],
                plan_row["id"],
                plan_row["billing_cycle"],
                json.dumps(
                    {
                        "plan_code": plan_code,
                        "monthly_price_brl": plan_row["monthly_price_brl"],
                    }
                ),
            ),
        )

        nx.conn_nx.commit()
        r.status = True
        r.message = success_message
        r.data = {
            "company_id": str(company["id"]),
            "role_id": str(role["id"]),
            "admin_user_id": str(user["id"]),
            "company_code": payload["company_code"],
            "admin_email": payload["admin_email"],
            "plan_code": plan_code,
            "plan_name": plan_row["name"],
        }
    except Exception as exc:
        nx.conn_nx.rollback()
        detail = str(exc)
        if "duplicate" in detail.lower() or "unique" in detail.lower():
            r.make_error(409, "Ja existe uma conta com esse codigo, e-mail ou documento")
        else:
            r.make_error(0, "Erro ao criar conta JurisFlow", detail)
    finally:
        nx.stop()

    return r


def bootstrap_company(payload: dict, setup_key: str) -> NXResult:
    r = NXResult()
    if not appConfig.setupKey:
        r.make_error(0, "JURISFLOW_SETUP_KEY nao configurada")
        return r

    if setup_key != appConfig.setupKey:
        r.make_error(401, "Setup key invalida")
        return r

    return _provision_company(payload, "Bootstrap inicial concluido com sucesso")


def public_signup_company(payload: dict) -> NXResult:
    return _provision_company(payload, "Conta JurisFlow criada com sucesso")

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from source.core.system.database import NXDatabaseConnection
from source.core.system.security import decode_token, encode_token, hash_password, verify_password
from source.core.system.utils import NXResult
from source.data.sql.sql_auth import SQL_ROLE_PERMISSIONS, SQL_USER_BY_COMPANY_EMAIL


def login_user(payload: dict) -> NXResult:
    r = NXResult()
    company_code = (payload.get("company_code") or "").strip()
    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""

    if not company_code or not email or not password:
        r.make_error(0, "company_code, email e password sao obrigatorios")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(SQL_USER_BY_COMPANY_EMAIL, (company_code, email))
        user = nx.xp_nx.fetchone()
        if not user or not user["active"]:
            r.make_error(401, "Usuario nao localizado ou inativo")
            return r

        if not verify_password(password, user["password_hash"]):
            r.make_error(401, "Credenciais invalidas")
            return r

        permissions = []
        if user.get("role_id"):
            nx.xp_nx.execute(SQL_ROLE_PERMISSIONS, (user["role_id"],))
            permissions = [row["code"] for row in nx.xp_nx.fetchall()]

        access_token = encode_token(
            {
                "user_id": str(user["id"]),
                "company_id": str(user["company_id"]),
                "company_code": user["company_code"],
                "scope": "tenant",
                "permissions": permissions,
            }
        )
        refresh_token = str(uuid4())
        expires_at = datetime.now(UTC) + timedelta(days=30)

        nx.xp_nx.execute(
            """
            INSERT INTO refresh_tokens (user_id, token, expires_at)
            VALUES (%s, %s, %s)
            """,
            (user["id"], refresh_token, expires_at),
        )
        nx.xp_nx.execute(
            """
            UPDATE users
            SET last_login_at = NOW(), updated_at = NOW()
            WHERE id = %s
            """,
            (user["id"],),
        )
        nx.conn_nx.commit()

        r.status = True
        r.message = "Login realizado com sucesso"
        r.data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": str(user["id"]),
                "name": user["name"],
                "email": user["email"],
                "company_code": user["company_code"],
                "company_name": user["company_name"],
                "role_name": user["role_name"],
                "permissions": permissions,
            },
        }
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao realizar login", str(exc))
    finally:
        nx.stop()

    return r


def refresh_access_token(payload: dict) -> NXResult:
    r = NXResult()
    refresh_token = (payload.get("refresh_token") or "").strip()
    if not refresh_token:
        r.make_error(0, "refresh_token e obrigatorio")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            """
            SELECT rt.user_id, rt.expires_at, rt.revoked_at, u.company_id, u.email, c.code AS company_code
            FROM refresh_tokens rt
            JOIN users u ON u.id = rt.user_id
            JOIN companies c ON c.id = u.company_id
            WHERE rt.token = %s
            LIMIT 1
            """,
            (refresh_token,),
        )
        row = nx.xp_nx.fetchone()
        if not row or row["revoked_at"] is not None or row["expires_at"] <= datetime.now(UTC):
            r.make_error(401, "Refresh token invalido ou expirado")
            return r

        access_token = encode_token(
            {
                "user_id": str(row["user_id"]),
                "company_id": str(row["company_id"]),
                "company_code": row["company_code"],
                "scope": "tenant",
            }
        )
        r.status = True
        r.message = "Token renovado com sucesso"
        r.data = {"access_token": access_token}
    except Exception as exc:
        r.make_error(0, "Erro ao renovar token", str(exc))
    finally:
        nx.stop()

    return r


def logout_refresh_token(payload: dict) -> NXResult:
    r = NXResult()
    refresh_token = (payload.get("refresh_token") or "").strip()
    if not refresh_token:
        r.make_error(0, "refresh_token e obrigatorio")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            """
            UPDATE refresh_tokens
            SET revoked_at = NOW()
            WHERE token = %s AND revoked_at IS NULL
            """,
            (refresh_token,),
        )
        nx.conn_nx.commit()
        r.status = True
        r.message = "Logout realizado com sucesso"
        r.data = {"revoked": nx.xp_nx.rowcount > 0}
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao realizar logout", str(exc))
    finally:
        nx.stop()

    return r


def validate_session(token: str) -> NXResult:
    r = NXResult()
    try:
        payload = decode_token(token)
        r.status = True
        r.message = "Sessao valida"
        r.data = payload
    except Exception as exc:
        r.make_error(401, "Sessao invalida", str(exc))
    return r


def change_password(session_payload: dict, payload: dict) -> NXResult:
    r = NXResult()
    current_password = payload.get("current_password") or ""
    new_password = payload.get("new_password") or ""
    if not current_password or not new_password:
        r.make_error(0, "current_password e new_password sao obrigatorios")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute("SELECT id, password_hash FROM users WHERE id = %s AND company_id = %s AND deleted_at IS NULL", (session_payload["user_id"], session_payload["company_id"]))
        user = nx.xp_nx.fetchone()
        if not user or not verify_password(current_password, user["password_hash"]):
            r.make_error(401, "Senha atual invalida")
            return r

        nx.xp_nx.execute("UPDATE users SET password_hash = %s, updated_at = NOW() WHERE id = %s", (hash_password(new_password), user["id"]))
        nx.conn_nx.commit()
        r.status = True
        r.message = "Senha alterada com sucesso"
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao alterar senha", str(exc))
    finally:
        nx.stop()

    return r


def request_password_reset(payload: dict) -> NXResult:
    r = NXResult()
    company_code = (payload.get("company_code") or "").strip()
    email = (payload.get("email") or "").strip()
    if not company_code or not email:
        r.make_error(0, "company_code e email sao obrigatorios")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(SQL_USER_BY_COMPANY_EMAIL, (company_code, email))
        user = nx.xp_nx.fetchone()
        if not user or not user["active"]:
            r.make_error(404, "Usuario nao localizado")
            return r

        reset_token = str(uuid4())
        expires_at = datetime.now(UTC) + timedelta(hours=2)
        nx.xp_nx.execute(
            """
            INSERT INTO password_reset_tokens (user_id, token, expires_at)
            VALUES (%s, %s, %s)
            """,
            (user["id"], reset_token, expires_at),
        )
        nx.conn_nx.commit()
        r.status = True
        r.message = "Solicitacao de reset registrada com sucesso"
        r.data = {
            "reset_token": reset_token,
            "expires_at": expires_at.isoformat(),
        }
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao solicitar reset de senha", str(exc))
    finally:
        nx.stop()

    return r


def reset_password(payload: dict) -> NXResult:
    r = NXResult()
    reset_token = (payload.get("reset_token") or "").strip()
    new_password = payload.get("new_password") or ""
    if not reset_token or not new_password:
        r.make_error(0, "reset_token e new_password sao obrigatorios")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            """
            SELECT prt.id, prt.user_id, prt.expires_at, prt.used_at
            FROM password_reset_tokens prt
            WHERE prt.token = %s
            LIMIT 1
            """,
            (reset_token,),
        )
        row = nx.xp_nx.fetchone()
        if not row or row["used_at"] is not None or row["expires_at"] <= datetime.now(UTC):
            r.make_error(401, "Token de reset invalido ou expirado")
            return r

        nx.xp_nx.execute(
            "UPDATE users SET password_hash = %s, updated_at = NOW() WHERE id = %s",
            (hash_password(new_password), row["user_id"]),
        )
        nx.xp_nx.execute(
            "UPDATE password_reset_tokens SET used_at = NOW() WHERE id = %s",
            (row["id"],),
        )
        nx.conn_nx.commit()
        r.status = True
        r.message = "Senha redefinida com sucesso"
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao redefinir senha", str(exc))
    finally:
        nx.stop()

    return r

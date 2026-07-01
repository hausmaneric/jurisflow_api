import json
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from source.core.config.config import appConfig
from source.core.system.database import NXDatabaseConnection
from source.core.system.security import decode_token, encode_token, hash_password, verify_password
from source.core.system.utils import NXResult
from source.data.sql.sql_auth import SQL_ROLE_PERMISSIONS, SQL_USER_BY_COMPANY_EMAIL, SQL_USERS_BY_EMAIL


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def _load_permissions(nx: NXDatabaseConnection, role_id) -> list[str]:
    if not role_id:
        return []

    nx.xp_nx.execute(SQL_ROLE_PERMISSIONS, (role_id,))
    return [row["code"] for row in nx.xp_nx.fetchall()]


def _issue_session(nx: NXDatabaseConnection, user: dict) -> tuple[str, str, list[str]]:
    permissions = _load_permissions(nx, user.get("role_id"))
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
    return access_token, refresh_token, permissions


def _session_user_payload(user: dict, permissions: list[str]) -> dict:
    return {
        "id": str(user["id"]),
        "name": user["name"],
        "email": user["email"],
        "company_code": user["company_code"],
        "company_name": user["company_name"],
        "role_name": user["role_name"],
        "permissions": permissions,
    }


def _oauth_redirect_uri() -> str:
    if appConfig.googleRedirectUri:
        return appConfig.googleRedirectUri
    if not appConfig.publicBaseUrl:
        return ""
    return appConfig.publicBaseUrl.rstrip("/") + "/api/v1/auth/google/callback"


def _web_google_callback_url() -> str:
    if appConfig.webBaseUrl:
        return appConfig.webBaseUrl.rstrip("/") + "/auth/google/callback"
    return "/auth/google/callback"


def _google_return_url(requested_url: str | None = None) -> str:
    web_callback = _web_google_callback_url()
    requested = (requested_url or "").strip()
    if requested == "jurisflow://auth/google":
        return requested
    return web_callback


def _redirect_with_params(base_url: str, params: dict) -> str:
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{urlencode(params)}"


def _redirect_with_fragment(base_url: str, params: dict) -> str:
    return f"{base_url}#{urlencode(params)}"


def _post_json(url: str, payload: dict) -> dict:
    body = urlencode(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_json(url: str, access_token: str) -> dict:
    request = Request(url, headers={"Authorization": f"Bearer {access_token}"}, method="GET")
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def login_user(payload: dict) -> NXResult:
    r = NXResult()
    company_code = (payload.get("company_code") or "").strip()
    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""

    if not email or not password:
        r.make_error(0, "email e password sao obrigatorios")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        if company_code:
            nx.xp_nx.execute(SQL_USER_BY_COMPANY_EMAIL, (company_code, email))
            user = nx.xp_nx.fetchone()
        else:
            nx.xp_nx.execute(SQL_USERS_BY_EMAIL, (email,))
            users = nx.xp_nx.fetchall()
            if len(users) > 1:
                r.make_error(400, "Informe o codigo do escritorio para esta conta")
                return r
            user = users[0] if users else None
        if not user or not user["active"]:
            r.make_error(401, "Usuario nao localizado ou inativo")
            return r

        if not verify_password(password, user["password_hash"]):
            r.make_error(401, "Credenciais invalidas")
            return r

        access_token, refresh_token, permissions = _issue_session(nx, user)
        nx.conn_nx.commit()

        r.status = True
        r.message = "Login realizado com sucesso"
        r.data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": _session_user_payload(user, permissions),
        }
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao realizar login", str(exc))
    finally:
        nx.stop()

    return r


def start_google_oauth(payload: dict) -> NXResult:
    r = NXResult()
    company_code = (payload.get("company_code") or "").strip().lower()
    redirect_uri = _oauth_redirect_uri()

    if not company_code:
        r.make_error(0, "company_code e obrigatorio para entrar com Google")
        return r
    return_url = _google_return_url(payload.get("return_url"))
    if not appConfig.googleClientId or not appConfig.googleClientSecret or not redirect_uri:
        r.make_error(
            0,
            "Login com Google nao configurado",
            "Configure JURISFLOW_GOOGLE_CLIENT_ID, JURISFLOW_GOOGLE_CLIENT_SECRET, JURISFLOW_GOOGLE_REDIRECT_URI e JURISFLOW_WEB_BASE_URL.",
        )
        return r

    state = encode_token(
        {
            "scope": "google_oauth_state",
            "company_code": company_code,
            "return_url": return_url,
            "nonce": str(uuid4()),
        },
        expires_in_hours=1,
    )
    auth_query = urlencode(
        {
            "client_id": appConfig.googleClientId,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
    )

    r.status = True
    r.message = "Redirecionamento Google gerado com sucesso"
    r.data = {
        "authorization_url": f"{GOOGLE_AUTH_URL}?{auth_query}",
        "redirect_uri": redirect_uri,
    }
    return r


def complete_google_oauth(args: dict) -> str:
    state_token = (args.get("state") or "").strip()
    code = (args.get("code") or "").strip()

    try:
        state = decode_token(state_token)
        return_url = _web_google_callback_url()
    except Exception:
        return _redirect_with_params(
            _web_google_callback_url(),
            {"error": "oauth_state", "message": "Sessao do Google expirada. Tente novamente."},
        )

    return_url = _google_return_url(state.get("return_url"))
    if state.get("scope") != "google_oauth_state" or not code:
        return _redirect_with_params(return_url, {"error": "oauth_callback", "message": "Retorno do Google invalido."})

    redirect_uri = _oauth_redirect_uri()
    try:
        token_data = _post_json(
            GOOGLE_TOKEN_URL,
            {
                "code": code,
                "client_id": appConfig.googleClientId,
                "client_secret": appConfig.googleClientSecret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        userinfo = _get_json(GOOGLE_USERINFO_URL, token_data["access_token"])
    except Exception as exc:
        return _redirect_with_params(return_url, {"error": "oauth_google", "message": f"Falha ao validar Google: {exc}"})

    email = (userinfo.get("email") or "").strip().lower()
    if not email or userinfo.get("email_verified") is False:
        return _redirect_with_params(return_url, {"error": "oauth_email", "message": "E-mail Google nao verificado."})

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return _redirect_with_params(return_url, {"error": "database", "message": opened.message})

    try:
        nx.xp_nx.execute(SQL_USER_BY_COMPANY_EMAIL, (state["company_code"], email))
        user = nx.xp_nx.fetchone()
        if not user or not user["active"]:
            return _redirect_with_params(
                return_url,
                {
                    "error": "oauth_user",
                    "message": "Este e-mail Google nao esta cadastrado neste escritorio.",
                },
            )

        access_token, refresh_token, permissions = _issue_session(nx, user)
        nx.conn_nx.commit()
        return _redirect_with_fragment(
            return_url,
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "company_code": user["company_code"],
                "email": user["email"],
                "name": user["name"],
            },
        )
    except Exception as exc:
        nx.conn_nx.rollback()
        return _redirect_with_params(return_url, {"error": "oauth_session", "message": str(exc)})
    finally:
        nx.stop()


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
            SELECT rt.user_id, rt.expires_at, rt.revoked_at, u.company_id, u.email, u.role_id, c.code AS company_code
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

        permissions = _load_permissions(nx, row.get("role_id"))
        access_token = encode_token(
            {
                "user_id": str(row["user_id"]),
                "company_id": str(row["company_id"]),
                "company_code": row["company_code"],
                "scope": "tenant",
                "permissions": permissions,
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
            "delivery_mode": "in_app",
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

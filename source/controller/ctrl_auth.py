from flask import redirect, request

from source.app import app
from source.core.system.utils import NXResult, get_bearer_token, get_session_payload
from source.logic.orb_auth import change_password, complete_google_oauth, login_user, logout_refresh_token, refresh_access_token, request_password_reset, reset_password, start_google_oauth, validate_session


def _response_status(result: NXResult, success_status: int = 200, default_error: int = 400) -> int:
    if result.status:
        return success_status
    return result.code if 400 <= result.code <= 599 else default_error


@app.route("/api/v1/auth/login", methods=["POST"])
def auth_login():
    payload = request.get_json(silent=True) or {}
    r = login_user(payload)
    return r.toJSON(), _response_status(r)


@app.route("/api/v1/auth/google/start", methods=["POST"])
def auth_google_start():
    payload = request.get_json(silent=True) or {}
    r = start_google_oauth(payload)
    return r.toJSON(), _response_status(r)


@app.route("/api/v1/auth/google/callback", methods=["GET"])
def auth_google_callback():
    return redirect(complete_google_oauth(request.args), code=302)


@app.route("/api/v1/auth/refresh", methods=["POST"])
def auth_refresh():
    payload = request.get_json(silent=True) or {}
    r = refresh_access_token(payload)
    return r.toJSON(), _response_status(r)


@app.route("/api/v1/auth/logout", methods=["POST"])
def auth_logout():
    payload = request.get_json(silent=True) or {}
    r = logout_refresh_token(payload)
    return r.toJSON(), _response_status(r)


@app.route("/api/v1/auth/session", methods=["GET"])
def auth_session():
    try:
        token = get_bearer_token()
    except Exception as exc:
        r = NXResult()
        r.make_error(401, "Falha na autenticacao", str(exc))
        return r.toJSON(), 401

    r = validate_session(token)
    return r.toJSON(), (200 if r.status else 401)


@app.route("/api/v1/auth/change-password", methods=["POST"])
def auth_change_password():
    try:
        session_payload = get_session_payload()
    except Exception as exc:
        r = NXResult()
        r.make_error(401, "Falha na autenticacao", str(exc))
        return r.toJSON(), 401

    payload = request.get_json(silent=True) or {}
    r = change_password(session_payload, payload)
    return r.toJSON(), _response_status(r)


@app.route("/api/v1/auth/request-password-reset", methods=["POST"])
def auth_request_password_reset():
    payload = request.get_json(silent=True) or {}
    r = request_password_reset(payload)
    return r.toJSON(), _response_status(r)


@app.route("/api/v1/auth/reset-password", methods=["POST"])
def auth_reset_password():
    payload = request.get_json(silent=True) or {}
    r = reset_password(payload)
    return r.toJSON(), _response_status(r)

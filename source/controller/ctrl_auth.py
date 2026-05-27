from flask import request

from source.app import app
from source.core.system.utils import NXResult, get_bearer_token, get_session_payload
from source.logic.orb_auth import change_password, login_user, logout_refresh_token, refresh_access_token, request_password_reset, reset_password, validate_session


@app.route("/api/v1/auth/login", methods=["POST"])
def auth_login():
    payload = request.get_json(silent=True) or {}
    r = login_user(payload)
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/auth/refresh", methods=["POST"])
def auth_refresh():
    payload = request.get_json(silent=True) or {}
    r = refresh_access_token(payload)
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/auth/logout", methods=["POST"])
def auth_logout():
    payload = request.get_json(silent=True) or {}
    r = logout_refresh_token(payload)
    return r.toJSON(), (200 if r.status else 400)


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
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/auth/request-password-reset", methods=["POST"])
def auth_request_password_reset():
    payload = request.get_json(silent=True) or {}
    r = request_password_reset(payload)
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/auth/reset-password", methods=["POST"])
def auth_reset_password():
    payload = request.get_json(silent=True) or {}
    r = reset_password(payload)
    return r.toJSON(), (200 if r.status else 400)

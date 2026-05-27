from flask import request

from source.app import app
from source.core.system.utils import NXResult, get_session_payload
from source.logic.orb_account import get_company_settings, get_current_user_profile, update_company_settings


@app.route("/api/v1/me", methods=["GET"])
def me():
    try:
        session_payload = get_session_payload()
    except Exception as exc:
        r = NXResult()
        r.make_error(401, "Falha na autenticacao", str(exc))
        return r.toJSON(), 401

    r = get_current_user_profile(session_payload)
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/company-settings", methods=["GET", "PUT"])
def company_settings():
    try:
        session_payload = get_session_payload()
    except Exception as exc:
        r = NXResult()
        r.make_error(401, "Falha na autenticacao", str(exc))
        return r.toJSON(), 401

    if request.method == "GET":
        r = get_company_settings(session_payload)
    else:
        payload = request.get_json(silent=True) or {}
        r = update_company_settings(session_payload, payload)
    return r.toJSON(), (200 if r.status else 400)

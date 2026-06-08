from flask import request

from source.app import app
from source.logic.orb_public import (
    create_client_portal_session,
    create_public_lead,
    get_public_company_profile,
    get_public_signature_request,
    sign_public_signature_request,
)


@app.route("/api/v1/public/companies/<company_code>", methods=["GET"])
def public_company_profile(company_code):
    r = get_public_company_profile(company_code)
    return r.toJSON(), (200 if r.status else 404)


@app.route("/api/v1/public/leads", methods=["POST"])
def public_leads():
    payload = request.get_json(silent=True) or {}
    r = create_public_lead(payload)
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/public/client-portal/session", methods=["POST"])
def public_client_portal_session():
    payload = request.get_json(silent=True) or {}
    r = create_client_portal_session(payload)
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/public/signatures/<token>", methods=["GET"])
def public_signature_request(token):
    r = get_public_signature_request(token)
    return r.toJSON(), (200 if r.status else 404)


@app.route("/api/v1/public/signatures/<token>/sign", methods=["POST"])
def public_signature_request_sign(token):
    payload = request.get_json(silent=True) or {}
    r = sign_public_signature_request(token, payload)
    return r.toJSON(), (200 if r.status else 400)

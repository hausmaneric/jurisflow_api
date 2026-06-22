from flask import request

from source.app import app
from source.logic.orb_setup import bootstrap_company, public_signup_company


def _response_status(result, success_status: int) -> int:
    if result.status:
        return success_status
    return result.code if 400 <= result.code <= 599 else 400


@app.route("/api/v1/setup/bootstrap", methods=["POST"])
def setup_bootstrap():
    payload = request.get_json(silent=True) or {}
    setup_key = request.headers.get("X-Setup-Key", "")
    r = bootstrap_company(payload, setup_key)
    return r.toJSON(), _response_status(r, 200)


@app.route("/api/v1/public/signup", methods=["POST"])
def public_signup():
    payload = request.get_json(silent=True) or {}
    r = public_signup_company(payload)
    return r.toJSON(), _response_status(r, 201)

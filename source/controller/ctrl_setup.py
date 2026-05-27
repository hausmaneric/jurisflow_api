from flask import request

from source.app import app
from source.logic.orb_setup import bootstrap_company


@app.route("/api/v1/setup/bootstrap", methods=["POST"])
def setup_bootstrap():
    payload = request.get_json(silent=True) or {}
    setup_key = request.headers.get("X-Setup-Key", "")
    r = bootstrap_company(payload, setup_key)
    return r.toJSON(), (200 if r.status else 400)

from flask import request

from source.app import app
from source.core.system.utils import NXResult, get_session_payload
from source.logic.orb_templates import generate_document, send_message_from_template


@app.route("/api/v1/documents/generate", methods=["POST"])
def document_generate():
    try:
        session_payload = get_session_payload()
    except Exception as exc:
        r = NXResult()
        r.make_error(401, "Falha na autenticacao", str(exc))
        return r.toJSON(), 401

    payload = request.get_json(silent=True) or {}
    r = generate_document(session_payload, payload)
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/messages/send-template", methods=["POST"])
def message_send_template():
    try:
        session_payload = get_session_payload()
    except Exception as exc:
        r = NXResult()
        r.make_error(401, "Falha na autenticacao", str(exc))
        return r.toJSON(), 401

    payload = request.get_json(silent=True) or {}
    r = send_message_from_template(session_payload, payload)
    return r.toJSON(), (200 if r.status else 400)

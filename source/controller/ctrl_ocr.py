from flask import request

from source.app import app
from source.core.system.utils import NXResult, get_session_payload
from source.logic.orb_ocr import get_document_ocr_result, process_document_ocr, update_document_ocr_result


@app.route("/api/v1/documents/<document_id>/ocr", methods=["GET", "POST", "PUT"])
def document_ocr(document_id):
    try:
        session_payload = get_session_payload()
    except Exception as exc:
        r = NXResult()
        r.make_error(401, "Falha na autenticacao", str(exc))
        return r.toJSON(), 401

    if request.method == "GET":
        r = get_document_ocr_result(document_id, session_payload)
        return r.toJSON(), (200 if r.status else 400)

    if request.method == "POST":
        r = process_document_ocr(document_id, session_payload)
        return r.toJSON(), (200 if r.status else 400)

    payload = request.get_json(silent=True) or {}
    r = update_document_ocr_result(document_id, payload, session_payload)
    return r.toJSON(), (200 if r.status else 400)

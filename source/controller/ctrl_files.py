from flask import Response, request

from source.app import app
from source.core.system.utils import NXResult, get_session_payload
from source.logic.orb_files import load_file_for_download, upload_document


@app.route("/api/v1/documents/upload", methods=["POST"])
def document_upload():
    try:
        session_payload = get_session_payload()
    except Exception as exc:
        r = NXResult()
        r.make_error(401, "Falha na autenticacao", str(exc))
        return r.toJSON(), 401

    payload = request.get_json(silent=True) or {}
    r = upload_document(session_payload, payload)
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/files/<stored_name>", methods=["GET"])
def file_download(stored_name):
    try:
        target, mime = load_file_for_download(stored_name)
        if not target.exists():
            r = NXResult()
            r.make_error(404, "Arquivo nao localizado")
            return r.toJSON(), 404
        return Response(target.read_bytes(), mimetype=mime, headers={"Content-Disposition": f'inline; filename="{target.name}"'})
    except Exception as exc:
        r = NXResult()
        r.make_error(0, "Erro ao carregar arquivo", str(exc))
        return r.toJSON(), 400

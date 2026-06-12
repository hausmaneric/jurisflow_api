from pathlib import Path

from flask import redirect, request, send_from_directory

from source.app import app
from source.core.system.storage import signed_download_url, storage_root, upload_file
from source.core.system.utils import NXResult, get_session_payload


@app.route("/api/v1/documents/upload", methods=["POST"])
def documents_upload():
    try:
        session_payload = get_session_payload()
    except Exception as exc:
        r = NXResult()
        r.make_error(401, "Falha na autenticacao", str(exc))
        return r.toJSON(), 401

    r = NXResult()
    file = request.files.get("file")
    if not file or not file.filename:
        r.make_error(0, "Arquivo nao informado")
        return r.toJSON(), 400

    try:
        stored = upload_file(file, str(session_payload.get("company_id") or "public"), "documents")
        r.status = True
        r.message = "Arquivo enviado com sucesso"
        r.data = stored.__dict__
        return r.toJSON(), 200
    except Exception as exc:
        r.make_error(0, "Erro ao enviar arquivo", str(exc))
        return r.toJSON(), 400


@app.route("/api/v1/uploads/<path:relative_path>/signed-url", methods=["GET"])
def uploaded_file_signed_url(relative_path: str):
    try:
        get_session_payload()
    except Exception as exc:
        r = NXResult()
        r.make_error(401, "Falha na autenticacao", str(exc))
        return r.toJSON(), 401

    r = NXResult()
    try:
        r.status = True
        r.message = "URL assinada gerada com sucesso"
        r.data = {"file_url": signed_download_url(relative_path)}
        return r.toJSON(), 200
    except Exception as exc:
        r.make_error(0, "Erro ao gerar URL assinada", str(exc))
        return r.toJSON(), 400


@app.route("/api/v1/uploads/<path:relative_path>", methods=["GET"])
def uploaded_file(relative_path: str):
    if str(relative_path).startswith(("documents/", "certificates/", "transcriptions/")):
        try:
            return redirect(signed_download_url(relative_path), code=302)
        except Exception:
            pass

    root = storage_root()
    target = (root / relative_path).resolve()
    if not str(target).startswith(str(root.resolve())) or not target.exists() or not target.is_file():
        r = NXResult()
        r.make_error(404, "Arquivo nao localizado")
        return r.toJSON(), 404

    return send_from_directory(target.parent, target.name, as_attachment=False)

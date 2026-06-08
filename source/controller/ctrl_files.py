from datetime import datetime
from pathlib import Path
from uuid import uuid4

from flask import request, send_from_directory
from werkzeug.utils import secure_filename

from source.app import app
from source.core.config.config import appConfig
from source.core.system.utils import NXResult, get_session_payload


def _storage_root() -> Path:
    root = Path(appConfig.storageRoot or "storage")
    if not root.is_absolute():
        root = Path(__file__).resolve().parents[3] / root
    return root


def _public_file_url(relative_path: str) -> str:
    base_url = (appConfig.publicBaseUrl or request.host_url.rstrip("/")).rstrip("/")
    normalized = relative_path.replace("\\", "/")
    return f"{base_url}/api/v1/uploads/{normalized}"


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

    original_name = secure_filename(file.filename)
    extension = Path(original_name).suffix.lower()
    timestamp = datetime.utcnow().strftime("%Y/%m/%d")
    company_id = str(session_payload.get("company_id") or "public")
    unique_name = f"{uuid4().hex}{extension}"
    relative_dir = Path("documents") / company_id / timestamp
    target_dir = _storage_root() / relative_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / unique_name
    file.save(target_path)

    relative_path = (relative_dir / unique_name).as_posix()
    r.status = True
    r.message = "Arquivo enviado com sucesso"
    r.data = {
        "file_name": original_name,
        "file_path": relative_path,
        "file_url": _public_file_url(relative_path),
        "file_type": extension.replace(".", "").upper() or "FILE",
        "size_bytes": target_path.stat().st_size,
    }
    return r.toJSON(), 200


@app.route("/api/v1/uploads/<path:relative_path>", methods=["GET"])
def uploaded_file(relative_path: str):
    root = _storage_root()
    target = (root / relative_path).resolve()
    if not str(target).startswith(str(root.resolve())) or not target.exists() or not target.is_file():
        r = NXResult()
        r.make_error(404, "Arquivo nao localizado")
        return r.toJSON(), 404

    return send_from_directory(target.parent, target.name, as_attachment=False)

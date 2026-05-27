import base64
import mimetypes
from pathlib import Path
from uuid import uuid4

from source.core.config.config import appConfig
from source.core.system.database import NXDatabaseConnection
from source.core.system.utils import NXResult
from source.logic.orb_audit import register_audit_log


def _storage_dir() -> Path:
    root = Path(__file__).resolve().parents[3] / appConfig.storageRoot
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_ext(filename: str) -> str:
    ext = Path(filename).suffix
    return ext[:12] if ext else ""


def _public_url(filename: str) -> str:
    return f"{appConfig.publicBaseUrl}/api/v1/files/{filename}"


def save_binary_file(filename: str, content: bytes) -> tuple[str, str]:
    stored_name = f"{uuid4().hex}{_safe_ext(filename)}"
    target = _storage_dir() / stored_name
    target.write_bytes(content)
    return stored_name, _public_url(stored_name)


def upload_document(session_payload: dict, payload: dict) -> NXResult:
    r = NXResult()
    filename = (payload.get("filename") or "").strip()
    content_b64 = payload.get("content_base64") or ""
    title = (payload.get("title") or filename).strip()
    if not filename or not content_b64 or not title:
        r.make_error(0, "filename, title e content_base64 sao obrigatorios")
        return r

    try:
        content = base64.b64decode(content_b64)
    except Exception as exc:
        r.make_error(0, "content_base64 invalido", str(exc))
        return r

    stored_name, public_url = save_binary_file(filename, content)
    file_type = payload.get("file_type") or mimetypes.guess_type(filename)[0] or "application/octet-stream"

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            """
            INSERT INTO documents (company_id, client_id, case_id, uploaded_by, title, file_url, file_type, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                session_payload["company_id"],
                payload.get("client_id"),
                payload.get("case_id"),
                session_payload.get("user_id"),
                title,
                public_url,
                file_type,
                payload.get("status") or "active",
            ),
        )
        row = nx.xp_nx.fetchone()
        nx.conn_nx.commit()
        register_audit_log(session_payload["company_id"], session_payload.get("user_id"), "documents", str(row["id"]), "upload", None, {"filename": filename, "stored_name": stored_name})
        r.status = True
        r.message = "Documento enviado com sucesso"
        r.data = {"id": str(row["id"]), "file_url": public_url, "stored_name": stored_name}
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao enviar documento", str(exc))
    finally:
        nx.stop()

    return r


def load_file_for_download(stored_name: str) -> tuple[Path, str]:
    target = _storage_dir() / stored_name
    mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    return target, mime

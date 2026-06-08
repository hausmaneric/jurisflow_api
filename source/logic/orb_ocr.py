import json
from pathlib import Path
from urllib.parse import urlparse

from source.core.config.config import appConfig
from source.core.system.database import NXDatabaseConnection
from source.core.system.utils import NXResult


def _storage_root() -> Path:
    root = Path(appConfig.storageRoot or "storage")
    if not root.is_absolute():
        root = Path(__file__).resolve().parents[3] / root
    return root.resolve()


def _file_path_from_url(file_url: str) -> Path | None:
    if not file_url:
        return None

    parsed = urlparse(file_url)
    marker = "/api/v1/uploads/"
    if marker not in parsed.path:
        return None

    relative = parsed.path.split(marker, 1)[1].lstrip("/")
    target = (_storage_root() / relative).resolve()
    if not str(target).startswith(str(_storage_root())):
        return None
    return target


def _extract_text_from_file(file_path: Path | None, document_row: dict) -> tuple[str, float, dict]:
    metadata = {
        "mode": "assistido",
        "file_type": document_row.get("file_type"),
        "file_name": Path(document_row.get("file_url") or "").name,
    }

    if not file_path or not file_path.exists() or not file_path.is_file():
        text = (
            f"Documento: {document_row.get('title') or 'Sem título'}\n"
            f"Tipo: {document_row.get('file_type') or 'Não informado'}\n"
            "OCR assistido: arquivo não disponível localmente para leitura direta.\n"
            "Use este resultado como rascunho inicial para revisão humana."
        )
        return text, 38.0, metadata

    extension = file_path.suffix.lower()
    metadata["extension"] = extension
    metadata["size_bytes"] = file_path.stat().st_size

    if extension in {".txt", ".md", ".csv", ".json", ".html", ".htm", ".xml"}:
        raw_text = file_path.read_text(encoding="utf-8", errors="ignore")
        cleaned = "\n".join(line.rstrip() for line in raw_text.splitlines()).strip()
        return cleaned[:30000] or "Arquivo textual sem conteúdo legível.", 96.0, metadata

    text = (
        f"Documento: {document_row.get('title') or 'Sem título'}\n"
        f"Tipo: {document_row.get('file_type') or extension.replace('.', '').upper() or 'Não informado'}\n"
        "OCR assistido: este formato exige etapa avançada de leitura visual.\n"
        "Resumo preliminar gerado para apoio operacional. Revise o conteúdo manualmente antes de usar em peças, prazos ou comunicações."
    )
    metadata["requires_visual_ocr"] = True
    return text, 54.0, metadata


def get_document_ocr_result(document_id: str, session_payload: dict) -> NXResult:
    r = NXResult()
    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            """
            SELECT id, company_id, document_id, requested_by, status, engine, source_file_url, extracted_text,
                   reviewed_text, confidence_score, extracted_metadata, created_at, updated_at
            FROM document_ocr_results
            WHERE company_id = %s AND document_id = %s AND deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (session_payload["company_id"], document_id),
        )
        row = nx.xp_nx.fetchone()
        r.status = True
        r.message = "Resultado OCR carregado com sucesso"
        r.data = dict(row) if row else {}
    except Exception as exc:
        r.make_error(0, "Erro ao carregar OCR do documento", str(exc))
    finally:
        nx.stop()

    return r


def process_document_ocr(document_id: str, session_payload: dict) -> NXResult:
    r = NXResult()
    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            """
            SELECT id, title, file_url, file_type, client_id, case_id
            FROM documents
            WHERE company_id = %s AND id = %s AND deleted_at IS NULL
            LIMIT 1
            """,
            (session_payload["company_id"], document_id),
        )
        document_row = nx.xp_nx.fetchone()
        if not document_row:
            r.make_error(404, "Documento nao localizado")
            return r

        file_path = _file_path_from_url(document_row.get("file_url") or "")
        extracted_text, confidence, metadata = _extract_text_from_file(file_path, document_row)

        nx.xp_nx.execute(
            """
            INSERT INTO document_ocr_results (
                company_id, document_id, requested_by, status, engine, source_file_url, extracted_text,
                reviewed_text, confidence_score, extracted_metadata, created_at, updated_at
            )
            VALUES (%s, %s, %s, 'processed', 'jurisflow-assisted-ocr', %s, %s, %s, %s, %s::jsonb, NOW(), NOW())
            RETURNING id, status, engine, source_file_url, extracted_text, reviewed_text, confidence_score, extracted_metadata, created_at, updated_at
            """,
            (
                session_payload["company_id"],
                document_id,
                session_payload.get("user_id"),
                document_row.get("file_url"),
                extracted_text,
                extracted_text,
                confidence,
                json.dumps(metadata, ensure_ascii=False),
            ),
        )
        row = nx.xp_nx.fetchone()
        nx.conn_nx.commit()

        r.status = True
        r.message = "OCR do documento processado com sucesso"
        r.data = dict(row)
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao processar OCR do documento", str(exc))
    finally:
        nx.stop()

    return r


def update_document_ocr_result(document_id: str, payload: dict, session_payload: dict) -> NXResult:
    r = NXResult()
    reviewed_text = (payload.get("reviewed_text") or "").strip()
    status = (payload.get("status") or "").strip().lower() or "reviewed"

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            """
            WITH latest AS (
                SELECT id
                FROM document_ocr_results
                WHERE company_id = %s
                  AND document_id = %s
                  AND deleted_at IS NULL
                ORDER BY created_at DESC
                LIMIT 1
            )
            UPDATE document_ocr_results ocr
            SET reviewed_text = %s,
                status = %s,
                updated_at = NOW()
            FROM latest
            WHERE ocr.id = latest.id
            RETURNING ocr.id, ocr.status, ocr.engine, ocr.source_file_url, ocr.extracted_text,
                      ocr.reviewed_text, ocr.confidence_score, ocr.extracted_metadata, ocr.created_at, ocr.updated_at
            """,
            (session_payload["company_id"], document_id, reviewed_text, status),
        )
        row = nx.xp_nx.fetchone()
        if not row:
            nx.conn_nx.rollback()
            r.make_error(404, "Resultado OCR nao localizado para este documento")
            return r

        nx.conn_nx.commit()
        r.status = True
        r.message = "OCR do documento atualizado com sucesso"
        r.data = dict(row)
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao atualizar OCR do documento", str(exc))
    finally:
        nx.stop()

    return r

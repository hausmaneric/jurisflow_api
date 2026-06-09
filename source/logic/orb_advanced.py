import json

from source.core.system.database import NXDatabaseConnection
from source.core.system.utils import NXResult
from source.logic.orb_audit import register_audit_log


def _has_permission(session_payload: dict, permission_code: str) -> bool:
    return permission_code in set(session_payload.get("permissions") or [])


def _json(value) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


def link_lawyer_user(lawyer_id: str, session_payload: dict, payload: dict) -> NXResult:
    r = NXResult()
    if not _has_permission(session_payload, "lawyers.write"):
        r.make_error(403, "Permissao insuficiente para vincular advogado")
        return r

    user_id = payload.get("user_id")
    if not user_id:
        r.make_error(0, "user_id e obrigatorio")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            """
            UPDATE lawyers
            SET user_id = %s, updated_at = NOW()
            WHERE id = %s AND company_id = %s AND deleted_at IS NULL
            RETURNING id, user_id, name, email, oab_number, oab_state
            """,
            (user_id, lawyer_id, session_payload["company_id"]),
        )
        row = nx.xp_nx.fetchone()
        if not row:
            r.make_error(404, "Advogado nao localizado")
            return r
        nx.conn_nx.commit()
        register_audit_log(session_payload["company_id"], session_payload.get("user_id"), "lawyers", lawyer_id, "link_user", None, {"user_id": user_id})
        r.status = True
        r.message = "Advogado vinculado ao usuario com sucesso"
        r.data = dict(row)
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao vincular advogado ao usuario", str(exc))
    finally:
        nx.stop()

    return r


def validate_lawyer_certificates(lawyer_id: str, session_payload: dict, payload: dict) -> NXResult:
    r = NXResult()
    if not _has_permission(session_payload, "lawyers.write"):
        r.make_error(403, "Permissao insuficiente para validar certificado")
        return r

    certificate_id = payload.get("certificate_id")
    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        params = [session_payload["company_id"], lawyer_id]
        certificate_filter = ""
        if certificate_id:
            certificate_filter = " AND id = %s"
            params.append(certificate_id)

        nx.xp_nx.execute(
            f"""
            UPDATE lawyer_certificates
            SET status = CASE
                    WHEN valid_until IS NOT NULL AND valid_until < CURRENT_DATE THEN 'expired'
                    ELSE 'valid'
                END,
                last_validated_at = NOW(),
                updated_at = NOW()
            WHERE company_id = %s AND lawyer_id = %s AND deleted_at IS NULL{certificate_filter}
            RETURNING id, lawyer_id, certificate_name, certificate_type, issuer, valid_from, valid_until, status, last_validated_at
            """,
            tuple(params),
        )
        rows = [dict(row) for row in nx.xp_nx.fetchall()]
        nx.conn_nx.commit()
        register_audit_log(session_payload["company_id"], session_payload.get("user_id"), "lawyer_certificates", certificate_id, "validate", None, {"lawyer_id": lawyer_id, "count": len(rows)})
        r.status = True
        r.message = "Certificado validado com sucesso" if certificate_id else "Certificados validados com sucesso"
        r.data = rows
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao validar certificado", str(exc))
    finally:
        nx.stop()

    return r


def sync_case(case_id: str, source: str, session_payload: dict, payload: dict) -> NXResult:
    r = NXResult()
    if not _has_permission(session_payload, "sync.write"):
        r.make_error(403, "Permissao insuficiente para sincronizar processo")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            "SELECT id, case_number, title, court FROM cases WHERE id = %s AND company_id = %s AND deleted_at IS NULL",
            (case_id, session_payload["company_id"]),
        )
        case_row = nx.xp_nx.fetchone()
        if not case_row:
            r.make_error(404, "Processo nao localizado")
            return r

        status = payload.get("status") or "success"
        raw_data = {
            "mode": "integration-controlled",
            "source": source,
            "message": "Sincronizacao registrada e controlada por conector configurado da empresa.",
            "provider_payload": payload.get("provider_payload") or {},
        }
        nx.xp_nx.execute(
            """
            INSERT INTO case_sync_logs (
                company_id, case_id, lawyer_id, source, court_system, status, started_at, finished_at,
                documents_found, documents_downloaded, movements_imported, error_message, raw_data, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW(), %s, %s, %s, %s, %s::jsonb, %s)
            RETURNING id, source, status, started_at, finished_at, documents_found, documents_downloaded, movements_imported
            """,
            (
                session_payload["company_id"],
                case_id,
                payload.get("lawyer_id"),
                source,
                payload.get("court_system"),
                status,
                int(payload.get("documents_found") or 0),
                int(payload.get("documents_downloaded") or 0),
                int(payload.get("movements_imported") or 0),
                payload.get("error_message"),
                _json(raw_data),
                session_payload.get("user_id"),
            ),
        )
        log_row = nx.xp_nx.fetchone()

        movement_title = payload.get("movement_title")
        if movement_title:
            nx.xp_nx.execute(
                """
                INSERT INTO case_movements (company_id, case_id, source, movement_code, movement_date, title, description, raw_data)
                VALUES (%s, %s, %s, %s, COALESCE(%s::date, CURRENT_DATE), %s, %s, %s::jsonb)
                """,
                (
                    session_payload["company_id"],
                    case_id,
                    source,
                    payload.get("movement_code"),
                    payload.get("movement_date"),
                    movement_title,
                    payload.get("movement_description"),
                    _json(payload.get("movement_raw_data")),
                ),
            )

        nx.conn_nx.commit()
        register_audit_log(session_payload["company_id"], session_payload.get("user_id"), "cases", case_id, f"sync_{source}", None, {"log_id": str(log_row["id"])})
        r.status = True
        r.message = "Sincronizacao registrada com sucesso"
        r.data = {"case": dict(case_row), "sync": dict(log_row)}
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao sincronizar processo", str(exc))
    finally:
        nx.stop()

    return r


def update_transcription_status(transcription_id: str, status: str, session_payload: dict, payload: dict | None = None) -> NXResult:
    r = NXResult()
    if not _has_permission(session_payload, "notes.write"):
        r.make_error(403, "Permissao insuficiente para alterar transcricao")
        return r

    payload = payload or {}
    finalized_sql = ", finalized_at = NOW()" if status == "finalized" else ""
    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            f"""
            UPDATE transcriptions
            SET status = %s, updated_at = NOW(){finalized_sql}
            WHERE id = %s AND company_id = %s AND deleted_at IS NULL
            RETURNING id, title, status, finalized_at, updated_at
            """,
            (status, transcription_id, session_payload["company_id"]),
        )
        row = nx.xp_nx.fetchone()
        if not row:
            r.make_error(404, "Transcricao nao localizada")
            return r
        nx.conn_nx.commit()
        register_audit_log(session_payload["company_id"], session_payload.get("user_id"), "transcriptions", transcription_id, status, None, payload)
        r.status = True
        r.message = "Transcricao atualizada com sucesso"
        r.data = dict(row)
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao atualizar transcricao", str(exc))
    finally:
        nx.stop()

    return r


def review_transcription(transcription_id: str, session_payload: dict, payload: dict) -> NXResult:
    r = NXResult()
    if not _has_permission(session_payload, "notes.write"):
        r.make_error(403, "Permissao insuficiente para revisar transcricao")
        return r

    reviewed_text = payload.get("reviewed_text")
    if not reviewed_text:
        r.make_error(0, "reviewed_text e obrigatorio")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            """
            INSERT INTO transcription_reviews (company_id, transcription_id, segment_id, original_text, reviewed_text, reviewed_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, transcription_id, segment_id, reviewed_text, reviewed_by, created_at
            """,
            (
                session_payload["company_id"],
                transcription_id,
                payload.get("segment_id"),
                payload.get("original_text"),
                reviewed_text,
                session_payload.get("user_id"),
            ),
        )
        review = nx.xp_nx.fetchone()
        if payload.get("segment_id"):
            nx.xp_nx.execute(
                """
                UPDATE transcription_segments
                SET reviewed = TRUE, text = %s, updated_at = NOW()
                WHERE id = %s AND transcription_id = %s AND company_id = %s
                """,
                (reviewed_text, payload.get("segment_id"), transcription_id, session_payload["company_id"]),
            )
        nx.conn_nx.commit()
        register_audit_log(session_payload["company_id"], session_payload.get("user_id"), "transcriptions", transcription_id, "review", None, {"review_id": str(review["id"])})
        r.status = True
        r.message = "Revisao registrada com sucesso"
        r.data = dict(review)
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao revisar transcricao", str(exc))
    finally:
        nx.stop()

    return r


def summarize_transcription(transcription_id: str, session_payload: dict, payload: dict) -> NXResult:
    r = NXResult()
    if not _has_permission(session_payload, "notes.write"):
        r.make_error(403, "Permissao insuficiente para resumir transcricao")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            """
            SELECT text
            FROM transcription_segments
            WHERE transcription_id = %s AND company_id = %s AND deleted_at IS NULL
            ORDER BY start_seconds NULLS LAST, created_at ASC
            """,
            (transcription_id, session_payload["company_id"]),
        )
        segments = [row["text"] for row in nx.xp_nx.fetchall()]
        summary = payload.get("summary") or (" ".join(segments)[:1200] if segments else "Resumo pendente de conteudo transcrito.")
        key_points = payload.get("key_points") or []
        next_steps = payload.get("next_steps") or []
        risks = payload.get("risks") or []
        nx.xp_nx.execute(
            """
            INSERT INTO transcription_summaries (company_id, transcription_id, summary, key_points, next_steps, risks, status, created_by)
            VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, 'generated', %s)
            RETURNING id, transcription_id, summary, key_points, next_steps, risks, status, created_at
            """,
            (session_payload["company_id"], transcription_id, summary, _json(key_points), _json(next_steps), _json(risks), session_payload.get("user_id")),
        )
        row = nx.xp_nx.fetchone()
        nx.conn_nx.commit()
        register_audit_log(session_payload["company_id"], session_payload.get("user_id"), "transcriptions", transcription_id, "summary", None, {"summary_id": str(row["id"])})
        r.status = True
        r.message = "Resumo gerado com sucesso"
        r.data = dict(row)
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao gerar resumo da transcricao", str(exc))
    finally:
        nx.stop()

    return r


def generate_transcription_tasks(transcription_id: str, session_payload: dict, payload: dict) -> NXResult:
    r = NXResult()
    if not _has_permission(session_payload, "notes.write"):
        r.make_error(403, "Permissao insuficiente para gerar tarefas da transcricao")
        return r

    tasks = payload.get("tasks") or []
    if not tasks:
        tasks = [{"title": "Revisar encaminhamentos da transcricao", "priority": "media", "status": "pending"}]

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        created = []
        for task in tasks:
            nx.xp_nx.execute(
                """
                INSERT INTO tasks (company_id, client_id, case_id, assigned_user_id, title, description, priority, due_at, status, created_by)
                SELECT company_id, client_id, case_id, %s, %s, %s, %s, %s, %s, %s
                FROM transcriptions
                WHERE id = %s AND company_id = %s AND deleted_at IS NULL
                RETURNING id, title, status
                """,
                (
                    task.get("assigned_user_id"),
                    task.get("title"),
                    task.get("description"),
                    task.get("priority") or "media",
                    task.get("due_at"),
                    task.get("status") or "pending",
                    session_payload.get("user_id"),
                    transcription_id,
                    session_payload["company_id"],
                ),
            )
            task_row = nx.xp_nx.fetchone()
            if task_row:
                nx.xp_nx.execute(
                    """
                    INSERT INTO transcription_tasks (company_id, transcription_id, task_id)
                    VALUES (%s, %s, %s)
                    """,
                    (session_payload["company_id"], transcription_id, task_row["id"]),
                )
                created.append(dict(task_row))
        nx.conn_nx.commit()
        register_audit_log(session_payload["company_id"], session_payload.get("user_id"), "transcriptions", transcription_id, "generate_tasks", None, {"count": len(created)})
        r.status = True
        r.message = "Tarefas geradas com sucesso"
        r.data = created
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao gerar tarefas da transcricao", str(exc))
    finally:
        nx.stop()

    return r


def upload_transcription_file(transcription_id: str, session_payload: dict, payload: dict) -> NXResult:
    r = NXResult()
    if not _has_permission(session_payload, "notes.write"):
        r.make_error(403, "Permissao insuficiente para enviar arquivo da transcricao")
        return r

    file_url = payload.get("file_url")
    if not file_url:
        r.make_error(0, "file_url e obrigatorio")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            """
            INSERT INTO transcription_files (company_id, transcription_id, file_url, file_type, duration_seconds, status)
            VALUES (%s, %s, %s, %s, %s, 'uploaded')
            RETURNING id, transcription_id, file_url, file_type, duration_seconds, status, created_at
            """,
            (
                session_payload["company_id"],
                transcription_id,
                file_url,
                payload.get("file_type"),
                payload.get("duration_seconds"),
            ),
        )
        row = nx.xp_nx.fetchone()
        nx.xp_nx.execute(
            "UPDATE transcriptions SET status = 'uploaded', updated_at = NOW() WHERE id = %s AND company_id = %s",
            (transcription_id, session_payload["company_id"]),
        )
        nx.conn_nx.commit()
        register_audit_log(session_payload["company_id"], session_payload.get("user_id"), "transcriptions", transcription_id, "upload", None, {"file_id": str(row["id"])})
        r.status = True
        r.message = "Arquivo de transcricao enviado com sucesso"
        r.data = dict(row)
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao enviar arquivo de transcricao", str(exc))
    finally:
        nx.stop()

    return r


def list_transcription_segments(transcription_id: str, session_payload: dict) -> NXResult:
    r = NXResult()
    if not _has_permission(session_payload, "notes.read"):
        r.make_error(403, "Permissao insuficiente para consultar segmentos")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            """
            SELECT id, transcription_id, speaker_label, start_seconds, end_seconds, text, confidence_score, reviewed, created_at, updated_at
            FROM transcription_segments
            WHERE transcription_id = %s AND company_id = %s AND deleted_at IS NULL
            ORDER BY start_seconds NULLS LAST, created_at ASC
            """,
            (transcription_id, session_payload["company_id"]),
        )
        r.status = True
        r.message = "Segmentos carregados com sucesso"
        r.data = [dict(row) for row in nx.xp_nx.fetchall()]
    except Exception as exc:
        r.make_error(0, "Erro ao carregar segmentos da transcricao", str(exc))
    finally:
        nx.stop()

    return r


def check_in_appointment(appointment_id: str, session_payload: dict, payload: dict) -> NXResult:
    r = NXResult()
    if not _has_permission(session_payload, "appointments.write"):
        r.make_error(403, "Permissao insuficiente para confirmar atendimento")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        notes = payload.get("notes") or "Check-in registrado pelo aplicativo."
        nx.xp_nx.execute(
            """
            UPDATE appointments
            SET status = %s,
                notes = CONCAT(COALESCE(notes, ''), CASE WHEN COALESCE(notes, '') = '' THEN '' ELSE E'\n' END, %s),
                updated_at = NOW()
            WHERE id = %s AND company_id = %s AND deleted_at IS NULL
            RETURNING id, title, status, location, meeting_url, start_at, end_at, notes
            """,
            (payload.get("status") or "done", notes, appointment_id, session_payload["company_id"]),
        )
        row = nx.xp_nx.fetchone()
        if not row:
            r.make_error(404, "Compromisso nao localizado")
            return r
        nx.conn_nx.commit()
        register_audit_log(session_payload["company_id"], session_payload.get("user_id"), "appointments", appointment_id, "check_in", None, payload)
        r.status = True
        r.message = "Check-in registrado com sucesso"
        r.data = dict(row)
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao registrar check-in", str(exc))
    finally:
        nx.stop()

    return r

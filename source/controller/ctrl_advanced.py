from flask import request

from source.app import app
from source.core.system.utils import NXResult, get_session_payload
from source.logic.orb_advanced import (
    diagnose_case_sync,
    export_transcription_document,
    export_transcription_note,
    generate_transcription_tasks,
    check_in_appointment,
    link_lawyer_user,
    list_transcription_segments,
    process_transcription,
    review_transcription,
    summarize_transcription,
    sync_case,
    update_transcription_status,
    upload_transcription_file,
    validate_lawyer_certificates,
)


def _session_or_error():
    try:
        return get_session_payload(), None
    except Exception as exc:
        r = NXResult()
        r.make_error(401, "Falha na autenticacao", str(exc))
        return None, (r.toJSON(), 401)


@app.route("/api/v1/lawyers/<lawyer_id>/link-user", methods=["POST", "PUT"])
def lawyer_link_user(lawyer_id):
    session_payload, error = _session_or_error()
    if error:
        return error
    r = link_lawyer_user(lawyer_id, session_payload, request.get_json(silent=True) or {})
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/lawyers/<lawyer_id>/certificates/validate", methods=["POST"])
def lawyer_certificates_validate(lawyer_id):
    session_payload, error = _session_or_error()
    if error:
        return error
    r = validate_lawyer_certificates(lawyer_id, session_payload, request.get_json(silent=True) or {})
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/cases/<case_id>/sync-datajud", methods=["POST"])
def case_sync_datajud(case_id):
    session_payload, error = _session_or_error()
    if error:
        return error
    r = sync_case(case_id, "datajud", session_payload, request.get_json(silent=True) or {})
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/cases/<case_id>/sync-diagnosis", methods=["GET"])
def case_sync_diagnosis(case_id):
    session_payload, error = _session_or_error()
    if error:
        return error
    r = diagnose_case_sync(case_id, session_payload, request.args.to_dict())
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/cases/<case_id>/sync-tribunal", methods=["POST"])
def case_sync_tribunal(case_id):
    session_payload, error = _session_or_error()
    if error:
        return error
    r = sync_case(case_id, "tribunal", session_payload, request.get_json(silent=True) or {})
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/cases/<case_id>/sync-full", methods=["POST"])
def case_sync_full(case_id):
    session_payload, error = _session_or_error()
    if error:
        return error
    r = sync_case(case_id, "full", session_payload, request.get_json(silent=True) or {})
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/transcriptions/<transcription_id>/start-recording", methods=["POST"])
def transcription_start_recording(transcription_id):
    session_payload, error = _session_or_error()
    if error:
        return error
    r = update_transcription_status(transcription_id, "recording", session_payload, request.get_json(silent=True) or {})
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/transcriptions/<transcription_id>/upload", methods=["POST"])
def transcription_upload(transcription_id):
    session_payload, error = _session_or_error()
    if error:
        return error
    r = upload_transcription_file(transcription_id, session_payload, request.get_json(silent=True) or {})
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/transcriptions/<transcription_id>/finish-recording", methods=["POST"])
def transcription_finish_recording(transcription_id):
    session_payload, error = _session_or_error()
    if error:
        return error
    r = update_transcription_status(transcription_id, "processing", session_payload, request.get_json(silent=True) or {})
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/transcriptions/<transcription_id>/process", methods=["POST"])
def transcription_process(transcription_id):
    session_payload, error = _session_or_error()
    if error:
        return error
    r = process_transcription(transcription_id, session_payload, request.get_json(silent=True) or {})
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/transcriptions/<transcription_id>/segments", methods=["GET"])
def transcription_segments_alias(transcription_id):
    session_payload, error = _session_or_error()
    if error:
        return error
    r = list_transcription_segments(transcription_id, session_payload)
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/transcriptions/<transcription_id>/review", methods=["POST"])
def transcription_review(transcription_id):
    session_payload, error = _session_or_error()
    if error:
        return error
    r = review_transcription(transcription_id, session_payload, request.get_json(silent=True) or {})
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/transcriptions/<transcription_id>/finalize", methods=["POST"])
def transcription_finalize(transcription_id):
    session_payload, error = _session_or_error()
    if error:
        return error
    r = update_transcription_status(transcription_id, "finalized", session_payload, request.get_json(silent=True) or {})
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/transcriptions/<transcription_id>/summary", methods=["POST"])
def transcription_summary(transcription_id):
    session_payload, error = _session_or_error()
    if error:
        return error
    r = summarize_transcription(transcription_id, session_payload, request.get_json(silent=True) or {})
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/transcriptions/<transcription_id>/generate-tasks", methods=["POST"])
def transcription_generate_tasks(transcription_id):
    session_payload, error = _session_or_error()
    if error:
        return error
    r = generate_transcription_tasks(transcription_id, session_payload, request.get_json(silent=True) or {})
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/transcriptions/<transcription_id>/export-note", methods=["POST"])
def transcription_export_note(transcription_id):
    session_payload, error = _session_or_error()
    if error:
        return error
    r = export_transcription_note(transcription_id, session_payload, request.get_json(silent=True) or {})
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/transcriptions/<transcription_id>/export-document", methods=["POST"])
def transcription_export_document(transcription_id):
    session_payload, error = _session_or_error()
    if error:
        return error
    r = export_transcription_document(transcription_id, session_payload, request.get_json(silent=True) or {})
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/appointments/<appointment_id>/check-in", methods=["POST"])
def appointment_check_in(appointment_id):
    session_payload, error = _session_or_error()
    if error:
        return error
    r = check_in_appointment(appointment_id, session_payload, request.get_json(silent=True) or {})
    return r.toJSON(), (200 if r.status else 400)

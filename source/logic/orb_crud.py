from flask import request

from source.core.system.database import NXDatabaseConnection
from source.core.system.security import hash_password
from source.core.system.utils import NXResult
from source.data.sql.sql_crud import RESOURCE_SELECT
from source.logic.orb_audit import register_audit_log


RESOURCE_CONFIG = {
    "companies": {
        "table": "companies",
        "permission_read": "companies.read",
        "permission_write": "companies.write",
        "required": [],
        "fields": ["name", "document", "email", "phone", "logo_url", "status"],
        "single": True,
        "soft_delete": True,
    },
    "users": {
        "table": "users",
        "permission_read": "users.read",
        "permission_write": "users.write",
        "required": ["name", "email", "password"],
        "fields": ["role_id", "name", "email", "password_hash", "phone", "status", "active"],
        "soft_delete": True,
    },
    "roles": {
        "table": "roles",
        "permission_read": "users.read",
        "permission_write": "users.write",
        "required": ["name"],
        "fields": ["name", "description", "is_admin", "active"],
    },
    "permissions": {
        "table": "permissions",
        "permission_read": "users.read",
        "permission_write": "users.read",
        "required": [],
        "fields": [],
        "catalog": True,
    },
    "role_permissions": {
        "table": "role_permissions",
        "permission_read": "users.read",
        "permission_write": "users.write",
        "required": ["role_id", "permission_id"],
        "fields": ["role_id", "permission_id"],
    },
    "company_subscriptions": {
        "table": "company_subscriptions",
        "permission_read": "subscriptions.read",
        "permission_write": "subscriptions.write",
        "required": [],
        "fields": ["plan_id", "status", "billing_cycle", "current_period_start", "current_period_end", "cancelled_at", "billing_data"],
        "soft_delete": True,
    },
    "clients": {
        "table": "clients",
        "permission_read": "clients.read",
        "permission_write": "clients.write",
        "required": ["name"],
        "fields": ["name", "document", "email", "phone", "birth_date", "notes", "status"],
        "soft_delete": True,
    },
    "client_contacts": {
        "table": "client_contacts",
        "permission_read": "clients.read",
        "permission_write": "clients.write",
        "required": ["client_id", "value"],
        "fields": ["client_id", "type", "label", "value", "is_primary", "notes"],
        "soft_delete": True,
    },
    "client_addresses": {
        "table": "client_addresses",
        "permission_read": "clients.read",
        "permission_write": "clients.write",
        "required": ["client_id"],
        "fields": ["client_id", "type", "street", "number", "complement", "district", "city", "state", "postal_code", "country", "is_primary", "notes"],
        "soft_delete": True,
    },
    "lawyers": {
        "table": "lawyers",
        "permission_read": "lawyers.read",
        "permission_write": "lawyers.write",
        "required": ["name"],
        "fields": ["user_id", "name", "email", "phone", "oab_number", "oab_state", "specialties", "active"],
        "soft_delete": True,
    },
    "lawyer_certificates": {
        "table": "lawyer_certificates",
        "permission_read": "lawyers.read",
        "permission_write": "lawyers.write",
        "required": ["lawyer_id", "certificate_name"],
        "fields": ["lawyer_id", "certificate_name", "certificate_file_url", "certificate_password_secret", "certificate_type", "issuer", "valid_from", "valid_until", "status", "consent_accepted", "consent_text", "last_validated_at", "created_by"],
        "soft_delete": True,
    },
    "cases": {
        "table": "cases",
        "permission_read": "cases.read",
        "permission_write": "cases.write",
        "required": ["title"],
        "fields": ["client_id", "lawyer_id", "case_number", "title", "area", "court", "district", "court_branch", "phase", "status", "notes"],
        "soft_delete": True,
    },
    "case_parties": {
        "table": "case_parties",
        "permission_read": "cases.read",
        "permission_write": "cases.write",
        "required": ["case_id", "name"],
        "fields": ["case_id", "client_id", "party_type", "name", "document", "email", "phone", "role_description", "notes"],
        "soft_delete": True,
    },
    "court_connectors": {
        "table": "court_connectors",
        "permission_read": "integrations.read",
        "permission_write": "integrations.write",
        "required": ["court_code", "court_name", "court_system"],
        "fields": ["court_code", "court_name", "court_system", "base_url", "status", "supports_public_lookup", "supports_certificate", "settings"],
        "soft_delete": True,
    },
    "case_sync_logs": {
        "table": "case_sync_logs",
        "permission_read": "sync.read",
        "permission_write": "sync.write",
        "required": ["case_id"],
        "fields": ["case_id", "lawyer_id", "source", "court_system", "status", "started_at", "finished_at", "documents_found", "documents_downloaded", "movements_imported", "error_message", "raw_data", "created_by"],
        "soft_delete": True,
    },
    "case_movements": {
        "table": "case_movements",
        "permission_read": "sync.read",
        "permission_write": "sync.write",
        "required": ["case_id", "title"],
        "fields": ["case_id", "source", "movement_code", "movement_date", "title", "description", "raw_data", "imported_at"],
        "soft_delete": True,
    },
    "case_documents_synced": {
        "table": "case_documents_synced",
        "permission_read": "sync.read",
        "permission_write": "sync.write",
        "required": ["case_id", "title"],
        "fields": ["case_id", "sync_log_id", "title", "source", "file_url", "file_type", "external_id", "status", "raw_data"],
        "soft_delete": True,
    },
    "automation_rules": {
        "table": "automation_rules",
        "permission_read": "integrations.read",
        "permission_write": "integrations.write",
        "required": ["name", "trigger_type"],
        "fields": ["name", "trigger_type", "conditions", "actions", "active", "created_by"],
        "soft_delete": True,
    },
    "ai_summaries": {
        "table": "ai_summaries",
        "permission_read": "ai.read",
        "permission_write": "ai.write",
        "required": ["entity", "summary"],
        "fields": ["entity", "entity_id", "summary_type", "summary", "next_steps", "risks", "source_data", "status", "created_by"],
        "soft_delete": True,
    },
    "appointments": {
        "table": "appointments",
        "permission_read": "appointments.read",
        "permission_write": "appointments.write",
        "required": ["title", "type", "start_at"],
        "fields": ["client_id", "case_id", "title", "type", "mode", "start_at", "end_at", "location", "notes", "status", "created_by"],
        "soft_delete": True,
    },
    "documents": {
        "table": "documents",
        "permission_read": "documents.read",
        "permission_write": "documents.write",
        "required": ["title", "file_url"],
        "fields": ["client_id", "case_id", "uploaded_by", "title", "file_url", "file_type", "status"],
        "soft_delete": True,
    },
    "document_categories": {
        "table": "document_categories",
        "permission_read": "documents.read",
        "permission_write": "documents.write",
        "required": ["name"],
        "fields": ["name", "slug", "description", "active"],
        "soft_delete": True,
    },
    "document_versions": {
        "table": "document_versions",
        "permission_read": "documents.read",
        "permission_write": "documents.write",
        "required": ["document_id", "file_url"],
        "fields": ["document_id", "created_by", "version_label", "title", "file_url", "file_type", "notes", "is_current"],
        "soft_delete": True,
    },
    "document_attachments": {
        "table": "document_attachments",
        "permission_read": "documents.read",
        "permission_write": "documents.write",
        "required": ["document_id", "title", "file_url"],
        "fields": ["document_id", "uploaded_by", "title", "file_url", "file_type", "notes"],
        "soft_delete": True,
    },
    "document_signature_requests": {
        "table": "document_signature_requests",
        "permission_read": "documents.read",
        "permission_write": "documents.write",
        "required": ["document_id", "signer_name"],
        "fields": [
            "document_id",
            "requester_user_id",
            "signer_name",
            "signer_email",
            "signer_document",
            "signer_role",
            "status",
            "access_token",
            "sent_at",
            "viewed_at",
            "signed_at",
            "cancelled_at",
            "notes",
        ],
        "soft_delete": True,
    },
    "document_templates": {
        "table": "document_templates",
        "permission_read": "document_templates.read",
        "permission_write": "document_templates.write",
        "required": ["name", "template_body"],
        "fields": ["name", "category", "file_type", "template_body", "variables", "active"],
        "soft_delete": True,
    },
    "generated_documents": {
        "table": "generated_documents",
        "permission_read": "documents.read",
        "permission_write": "documents.write",
        "required": ["title"],
        "fields": ["template_id", "client_id", "case_id", "document_id", "title", "output_format", "file_url", "context", "status", "generated_by"],
        "soft_delete": True,
    },
    "message_templates": {
        "table": "message_templates",
        "permission_read": "message_templates.read",
        "permission_write": "message_templates.write",
        "required": ["name", "body"],
        "fields": ["name", "channel", "subject", "body", "active"],
    },
    "messages": {
        "table": "messages",
        "permission_read": "messages.read",
        "permission_write": "messages.write",
        "required": ["recipient", "body"],
        "fields": ["client_id", "case_id", "template_id", "channel", "recipient", "subject", "body", "status", "sent_at", "created_by"],
    },
    "financial_entries": {
        "table": "financial_entries",
        "permission_read": "financial.read",
        "permission_write": "financial.write",
        "required": ["description", "entry_type", "category", "amount"],
        "fields": ["client_id", "case_id", "created_by", "entry_date", "description", "entry_type", "category", "account_label", "amount", "status", "notes"],
        "soft_delete": True,
    },
    "message_attachments": {
        "table": "message_attachments",
        "permission_read": "messages.read",
        "permission_write": "messages.write",
        "required": ["message_id", "title", "file_url"],
        "fields": ["message_id", "uploaded_by", "title", "file_url", "file_type", "notes"],
        "soft_delete": True,
    },
    "tasks": {
        "table": "tasks",
        "permission_read": "tasks.read",
        "permission_write": "tasks.write",
        "required": ["title"],
        "fields": ["client_id", "case_id", "assigned_user_id", "title", "description", "priority", "due_at", "status", "created_by"],
        "soft_delete": True,
    },
    "notifications": {
        "table": "notifications",
        "permission_read": "notifications.read",
        "permission_write": "notifications.write",
        "required": ["title", "body"],
        "fields": ["user_id", "title", "body", "channel", "scheduled_at", "sent_at", "read_at", "attempts", "status"],
    },
    "webhooks": {
        "table": "webhooks",
        "permission_read": "integrations.read",
        "permission_write": "integrations.write",
        "required": ["name", "target_url"],
        "fields": ["name", "target_url", "events", "secret", "active", "last_status", "last_called_at", "created_by"],
        "soft_delete": True,
    },
    "webhook_deliveries": {
        "table": "webhook_deliveries",
        "permission_read": "integrations.read",
        "permission_write": "integrations.write",
        "required": ["webhook_id", "event_name"],
        "fields": ["webhook_id", "event_name", "payload", "status", "response_code", "response_body", "attempts", "next_retry_at", "delivered_at"],
        "soft_delete": True,
    },
    "api_tokens": {
        "table": "api_tokens",
        "permission_read": "integrations.read",
        "permission_write": "integrations.write",
        "required": ["name", "token_hash"],
        "fields": ["name", "token_hash", "scopes", "rate_limit_per_minute", "status", "last_used_at", "expires_at", "created_by"],
        "soft_delete": True,
    },
    "notes": {
        "table": "notes",
        "permission_read": "notes.read",
        "permission_write": "notes.write",
        "required": ["title", "content"],
        "fields": ["client_id", "case_id", "appointment_id", "task_id", "document_id", "title", "content", "type", "visibility", "created_by"],
        "soft_delete": True,
    },
    "transcriptions": {
        "table": "transcriptions",
        "permission_read": "notes.read",
        "permission_write": "notes.write",
        "required": ["title"],
        "fields": ["client_id", "case_id", "appointment_id", "title", "source", "transcription_type", "status", "language", "quality_score", "consent_confirmed", "confidentiality", "created_by", "finalized_at"],
        "soft_delete": True,
    },
    "transcription_files": {
        "table": "transcription_files",
        "permission_read": "notes.read",
        "permission_write": "notes.write",
        "required": ["transcription_id", "file_url"],
        "fields": ["transcription_id", "file_url", "file_type", "duration_seconds", "status"],
        "soft_delete": True,
    },
    "transcription_segments": {
        "table": "transcription_segments",
        "permission_read": "notes.read",
        "permission_write": "notes.write",
        "required": ["transcription_id", "text"],
        "fields": ["transcription_id", "speaker_label", "start_seconds", "end_seconds", "text", "confidence_score", "reviewed"],
        "soft_delete": True,
    },
    "transcription_reviews": {
        "table": "transcription_reviews",
        "permission_read": "notes.read",
        "permission_write": "notes.write",
        "required": ["transcription_id", "reviewed_text"],
        "fields": ["transcription_id", "segment_id", "original_text", "reviewed_text", "reviewed_by"],
    },
    "transcription_summaries": {
        "table": "transcription_summaries",
        "permission_read": "notes.read",
        "permission_write": "notes.write",
        "required": ["transcription_id", "summary"],
        "fields": ["transcription_id", "summary", "key_points", "next_steps", "risks", "status", "created_by"],
        "soft_delete": True,
    },
    "transcription_tasks": {
        "table": "transcription_tasks",
        "permission_read": "notes.read",
        "permission_write": "notes.write",
        "required": ["transcription_id", "task_id"],
        "fields": ["transcription_id", "task_id"],
    },
    "appointment_participants": {
        "table": "appointment_participants",
        "permission_read": "appointments.read",
        "permission_write": "appointments.write",
        "required": ["appointment_id"],
        "fields": ["appointment_id", "user_id", "lawyer_id", "participant_name", "participant_type"],
    },
    "task_checklist_items": {
        "table": "task_checklist_items",
        "permission_read": "tasks.read",
        "permission_write": "tasks.write",
        "required": ["task_id", "title"],
        "fields": ["task_id", "title", "done"],
    },
    "audit_logs": {
        "table": "audit_logs",
        "permission_read": "audit.read",
        "permission_write": "audit.read",
        "required": [],
        "fields": [],
    },
}


def _has_permission(session_payload: dict, permission_code: str) -> bool:
    permissions = set(session_payload.get("permissions") or [])
    return permission_code in permissions


def _audit_safe_payload(payload: dict) -> dict:
    safe = dict(payload)
    if "password" in safe:
        safe["password"] = "***"
    if "password_hash" in safe:
        safe["password_hash"] = "***"
    return safe


def _normalize_messages_payload(payload: dict, session_payload: dict) -> dict:
    prepared = dict(payload)
    status = (prepared.get("status") or "").strip().lower()

    if not prepared.get("created_by") and session_payload.get("user_id"):
        prepared["created_by"] = session_payload["user_id"]

    if status == "sent" and not prepared.get("sent_at"):
        prepared["sent_at"] = "NOW()"
    elif status in {"draft", "queued", "scheduled", "failed"} and "sent_at" not in prepared:
        prepared["sent_at"] = None

    return prepared


def _normalize_document_version_payload(payload: dict, session_payload: dict) -> dict:
    prepared = dict(payload)

    if not prepared.get("created_by") and session_payload.get("user_id"):
        prepared["created_by"] = session_payload["user_id"]

    if prepared.get("is_current") in ("true", "True", 1, "1"):
        prepared["is_current"] = True
    elif prepared.get("is_current") in ("false", "False", 0, "0"):
        prepared["is_current"] = False

    return prepared


def _normalize_signature_request_payload(payload: dict, session_payload: dict) -> dict:
    prepared = dict(payload)

    if not prepared.get("requester_user_id") and session_payload.get("user_id"):
        prepared["requester_user_id"] = session_payload["user_id"]

    status = str(prepared.get("status") or "pending").strip().lower()
    prepared["status"] = status

    if status == "sent" and not prepared.get("sent_at"):
        prepared["sent_at"] = "NOW()"
    if status == "viewed" and not prepared.get("viewed_at"):
        prepared["viewed_at"] = "NOW()"
    if status == "signed" and not prepared.get("signed_at"):
        prepared["signed_at"] = "NOW()"
    if status == "cancelled" and not prepared.get("cancelled_at"):
        prepared["cancelled_at"] = "NOW()"

    return prepared


def _build_sql_value(field: str, value):
    if field in {"sent_at", "viewed_at", "signed_at", "cancelled_at", "last_validated_at", "started_at", "finished_at", "imported_at", "finalized_at", "delivered_at", "last_called_at", "last_used_at"} and value == "NOW()":
        return "NOW()", []
    return "%s", [value]


def _sync_current_document_version(nx: NXDatabaseConnection, company_id: str, document_id: str, current_version_id: str) -> None:
    nx.xp_nx.execute(
        """
        UPDATE document_versions
        SET is_current = FALSE, updated_at = NOW()
        WHERE company_id = %s AND document_id = %s AND id <> %s AND deleted_at IS NULL
        """,
        (company_id, document_id, current_version_id),
    )


def _apply_filters(resource_name: str, sql: str, params: list) -> tuple[str, list]:
    allowed = {
        "users": {"status", "active"},
        "roles": {"active"},
        "role_permissions": {"role_id", "permission_id"},
        "company_subscriptions": {"status", "plan_id"},
        "clients": {"status"},
        "client_contacts": {"client_id", "type", "is_primary"},
        "client_addresses": {"client_id", "type", "is_primary"},
        "lawyers": {"active"},
        "lawyer_certificates": {"lawyer_id", "status", "certificate_type"},
        "cases": {"status", "client_id", "lawyer_id", "area", "phase"},
        "case_parties": {"case_id", "client_id", "party_type"},
        "court_connectors": {"court_code", "court_system", "status"},
        "case_sync_logs": {"case_id", "lawyer_id", "source", "court_system", "status"},
        "case_movements": {"case_id", "source"},
        "case_documents_synced": {"case_id", "sync_log_id", "source", "status"},
        "automation_rules": {"trigger_type", "active"},
        "ai_summaries": {"entity", "entity_id", "summary_type", "status"},
        "appointments": {"status", "client_id", "case_id"},
        "documents": {"status", "client_id", "case_id"},
        "document_categories": {"active"},
        "document_versions": {"document_id", "is_current"},
        "document_attachments": {"document_id"},
        "document_signature_requests": {"document_id", "status"},
        "document_templates": {"active"},
        "generated_documents": {"template_id", "client_id", "case_id", "document_id", "status"},
        "message_templates": {"active", "channel"},
        "messages": {"status", "client_id", "case_id", "channel"},
        "financial_entries": {"entry_type", "status", "client_id", "case_id", "category"},
        "message_attachments": {"message_id"},
        "tasks": {"status", "client_id", "case_id", "assigned_user_id", "priority"},
        "notifications": {"status", "channel"},
        "webhooks": {"active", "last_status"},
        "webhook_deliveries": {"webhook_id", "event_name", "status"},
        "api_tokens": {"status"},
        "notes": {"client_id", "case_id", "appointment_id", "task_id", "document_id", "type", "visibility"},
        "transcriptions": {"client_id", "case_id", "appointment_id", "status", "source", "transcription_type"},
        "transcription_files": {"transcription_id", "status"},
        "transcription_segments": {"transcription_id", "reviewed"},
        "transcription_reviews": {"transcription_id", "segment_id", "reviewed_by"},
        "transcription_summaries": {"transcription_id", "status"},
        "transcription_tasks": {"transcription_id", "task_id"},
        "appointment_participants": {"appointment_id", "user_id", "lawyer_id", "participant_type"},
        "task_checklist_items": {"task_id", "done"},
    }

    for field in allowed.get(resource_name, set()):
        value = request.args.get(field)
        if value not in (None, ""):
            sql = sql.replace("ORDER BY", f" AND {field} = %s ORDER BY", 1)
            params.append(value)

    if resource_name == "audit_logs":
        action = request.args.get("action")
        if action:
            sql = sql.replace("ORDER BY created_at DESC", " AND action = %s ORDER BY created_at DESC")
            params.append(action)

    search = request.args.get("search")
    search_fields = {
        "clients": "(name ILIKE %s OR email ILIKE %s OR document ILIKE %s)",
        "lawyers": "(name ILIKE %s OR email ILIKE %s OR oab_number ILIKE %s)",
        "cases": "(title ILIKE %s OR case_number ILIKE %s OR court ILIKE %s)",
        "case_parties": "(name ILIKE %s OR document ILIKE %s OR role_description ILIKE %s)",
        "court_connectors": "(court_code ILIKE %s OR court_name ILIKE %s OR court_system ILIKE %s)",
        "case_movements": "(title ILIKE %s OR description ILIKE %s OR movement_code ILIKE %s)",
        "documents": "(title ILIKE %s OR file_type ILIKE %s OR file_url ILIKE %s)",
        "document_categories": "(name ILIKE %s OR slug ILIKE %s OR description ILIKE %s)",
        "generated_documents": "(title ILIKE %s OR output_format ILIKE %s OR status ILIKE %s)",
        "tasks": "(title ILIKE %s OR description ILIKE %s OR status ILIKE %s)",
        "message_templates": "(name ILIKE %s OR body ILIKE %s OR subject ILIKE %s)",
        "messages": "(recipient ILIKE %s OR subject ILIKE %s OR body ILIKE %s)",
        "financial_entries": "(description ILIKE %s OR category ILIKE %s OR account_label ILIKE %s)",
        "webhooks": "(name ILIKE %s OR target_url ILIKE %s OR last_status ILIKE %s)",
        "api_tokens": "(name ILIKE %s OR status ILIKE %s OR created_by::text ILIKE %s)",
        "notes": "(title ILIKE %s OR content ILIKE %s OR type ILIKE %s)",
        "transcriptions": "(title ILIKE %s OR source ILIKE %s OR status ILIKE %s)",
        "transcription_segments": "(speaker_label ILIKE %s OR text ILIKE %s OR reviewed::text ILIKE %s)",
        "transcription_summaries": "(summary ILIKE %s OR status ILIKE %s OR created_by::text ILIKE %s)",
    }
    if search and resource_name in search_fields:
        sql = sql.replace("ORDER BY", f" AND {search_fields[resource_name]} ORDER BY", 1)
        term = f"%{search}%"
        params.extend([term, term, term])

    limit = request.args.get("limit")
    if limit not in (None, ""):
        sql += " LIMIT %s"
        params.append(int(limit))

    return sql, params


def list_resource(resource_name: str, session_payload: dict) -> NXResult:
    r = NXResult()
    config = RESOURCE_CONFIG[resource_name]
    if not _has_permission(session_payload, config["permission_read"]):
        r.make_error(403, "Permissao insuficiente para consulta")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        sql = RESOURCE_SELECT[resource_name]
        params = [session_payload["company_id"]]
        if resource_name != "companies":
            sql, params = _apply_filters(resource_name, sql, params)
        nx.xp_nx.execute(sql, tuple(params))
        rows = nx.xp_nx.fetchall()
        r.status = True
        r.message = "Consulta realizada com sucesso"
        if config.get("single"):
            r.data = dict(rows[0]) if rows else {}
        else:
            r.data = [dict(row) for row in rows]
    except Exception as exc:
        r.make_error(0, "Erro ao consultar registros", str(exc))
    finally:
        nx.stop()

    return r


def create_resource(resource_name: str, payload: dict, session_payload: dict) -> NXResult:
    r = NXResult()
    config = RESOURCE_CONFIG[resource_name]
    if not _has_permission(session_payload, config["permission_write"]):
        r.make_error(403, "Permissao insuficiente para criacao")
        return r

    missing = [field for field in config["required"] if not payload.get(field)]
    if missing:
        r.make_error(0, f"Campos obrigatorios ausentes: {', '.join(missing)}")
        return r

    prepared_payload = dict(payload)
    if resource_name == "users" and payload.get("password"):
        prepared_payload["password_hash"] = hash_password(payload["password"])
    if resource_name == "messages":
        prepared_payload = _normalize_messages_payload(prepared_payload, session_payload)
    if resource_name == "document_versions":
        prepared_payload = _normalize_document_version_payload(prepared_payload, session_payload)
    if resource_name == "document_signature_requests":
        prepared_payload = _normalize_signature_request_payload(prepared_payload, session_payload)

    dynamic_fields = [field for field in config["fields"] if field in prepared_payload]
    fields = ["company_id"] + dynamic_fields
    values = [session_payload["company_id"]]
    placeholder_tokens = ["%s"]
    for field in dynamic_fields:
        token, token_values = _build_sql_value(field, prepared_payload[field])
        placeholder_tokens.append(token)
        values.extend(token_values)
    placeholders = ", ".join(placeholder_tokens)
    columns = ", ".join(fields)

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            f"INSERT INTO {config['table']} ({columns}) VALUES ({placeholders}) RETURNING id",
            values,
        )
        row = nx.xp_nx.fetchone()
        if resource_name == "document_versions" and prepared_payload.get("is_current"):
            _sync_current_document_version(
                nx,
                session_payload["company_id"],
                prepared_payload["document_id"],
                str(row["id"]),
            )
        nx.conn_nx.commit()
        register_audit_log(session_payload["company_id"], session_payload.get("user_id"), resource_name, str(row["id"]), "create", None, _audit_safe_payload(prepared_payload))
        r.status = True
        r.message = "Registro cadastrado com sucesso"
        r.data = {"id": str(row["id"])}
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao cadastrar registro", str(exc))
    finally:
        nx.stop()

    return r


def get_resource_by_id(resource_name: str, record_id: str, session_payload: dict) -> NXResult:
    r = NXResult()
    config = RESOURCE_CONFIG[resource_name]
    if not _has_permission(session_payload, config["permission_read"]):
        r.make_error(403, "Permissao insuficiente para consulta")
        return r

    sql = f"SELECT * FROM {config['table']} WHERE id = %s AND company_id = %s"
    if config.get("soft_delete"):
        sql += " AND deleted_at IS NULL"

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(sql, (record_id, session_payload["company_id"]))
        row = nx.xp_nx.fetchone()
        if not row:
            r.make_error(404, "Registro nao localizado")
        else:
            r.status = True
            r.message = "Registro carregado com sucesso"
            r.data = dict(row)
    except Exception as exc:
        r.make_error(0, "Erro ao consultar registro", str(exc))
    finally:
        nx.stop()

    return r


def update_resource(resource_name: str, record_id: str, payload: dict, session_payload: dict) -> NXResult:
    r = NXResult()
    config = RESOURCE_CONFIG[resource_name]
    if not _has_permission(session_payload, config["permission_write"]):
        r.make_error(403, "Permissao insuficiente para edicao")
        return r

    prepared_payload = dict(payload)
    if resource_name == "users" and payload.get("password"):
        prepared_payload["password_hash"] = hash_password(payload["password"])
    if resource_name == "messages":
        prepared_payload = _normalize_messages_payload(prepared_payload, session_payload)
    if resource_name == "document_versions":
        prepared_payload = _normalize_document_version_payload(prepared_payload, session_payload)
    if resource_name == "document_signature_requests":
        prepared_payload = _normalize_signature_request_payload(prepared_payload, session_payload)

    fields = [field for field in config["fields"] if field in prepared_payload]
    if not fields:
        r.make_error(0, "Nenhum campo valido informado para atualizacao")
        return r

    assignments = []
    params = []
    for field in fields:
        token, token_values = _build_sql_value(field, prepared_payload[field])
        assignments.append(f"{field} = {token}")
        params.extend(token_values)
    set_clause = ", ".join(assignments + ["updated_at = NOW()"])
    params.extend([record_id, session_payload["company_id"]])
    sql = f"UPDATE {config['table']} SET {set_clause} WHERE id = %s AND company_id = %s"
    if config.get("soft_delete"):
        sql += " AND deleted_at IS NULL"
    sql += " RETURNING id"

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(sql, params)
        row = nx.xp_nx.fetchone()
        if not row:
            nx.conn_nx.rollback()
            r.make_error(404, "Registro nao localizado")
            return r
        if resource_name == "document_versions" and prepared_payload.get("is_current"):
            nx.xp_nx.execute(
                """
                SELECT document_id
                FROM document_versions
                WHERE id = %s AND company_id = %s AND deleted_at IS NULL
                """,
                (record_id, session_payload["company_id"]),
            )
            version_row = nx.xp_nx.fetchone()
            if version_row:
                _sync_current_document_version(
                    nx,
                    session_payload["company_id"],
                    version_row["document_id"],
                    record_id,
                )
        nx.conn_nx.commit()
        register_audit_log(session_payload["company_id"], session_payload.get("user_id"), resource_name, record_id, "update", None, _audit_safe_payload(prepared_payload))
        r.status = True
        r.message = "Registro atualizado com sucesso"
        r.data = {"id": str(row["id"])}
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao atualizar registro", str(exc))
    finally:
        nx.stop()

    return r


def delete_resource(resource_name: str, record_id: str, session_payload: dict) -> NXResult:
    r = NXResult()
    config = RESOURCE_CONFIG[resource_name]
    if not _has_permission(session_payload, config["permission_write"]):
        r.make_error(403, "Permissao insuficiente para exclusao")
        return r

    if resource_name == "companies":
        r.make_error(400, "Exclusao da empresa nao suportada por esta rota")
        return r

    if config.get("soft_delete"):
        sql = f"UPDATE {config['table']} SET deleted_at = NOW(), updated_at = NOW() WHERE id = %s AND company_id = %s AND deleted_at IS NULL RETURNING id"
    else:
        sql = f"DELETE FROM {config['table']} WHERE id = %s AND company_id = %s RETURNING id"

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(sql, (record_id, session_payload["company_id"]))
        row = nx.xp_nx.fetchone()
        if not row:
            nx.conn_nx.rollback()
            r.make_error(404, "Registro nao localizado")
            return r
        nx.conn_nx.commit()
        register_audit_log(session_payload["company_id"], session_payload.get("user_id"), resource_name, record_id, "delete", None, None)
        r.status = True
        r.message = "Registro removido com sucesso"
        r.data = {"id": str(row["id"])}
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao remover registro", str(exc))
    finally:
        nx.stop()

    return r

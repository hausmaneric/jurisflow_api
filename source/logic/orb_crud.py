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
    "clients": {
        "table": "clients",
        "permission_read": "clients.read",
        "permission_write": "clients.write",
        "required": ["name"],
        "fields": ["name", "document", "email", "phone", "birth_date", "notes", "status"],
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
    "cases": {
        "table": "cases",
        "permission_read": "cases.read",
        "permission_write": "cases.write",
        "required": ["title"],
        "fields": ["client_id", "lawyer_id", "case_number", "title", "area", "court", "district", "court_branch", "phase", "status", "notes"],
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
    if field == "sent_at" and value == "NOW()":
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
        "clients": {"status"},
        "lawyers": {"active"},
        "cases": {"status", "client_id"},
        "appointments": {"status", "client_id", "case_id"},
        "documents": {"status", "client_id", "case_id"},
        "document_versions": {"document_id", "is_current"},
        "document_attachments": {"document_id"},
        "document_signature_requests": {"document_id", "status"},
        "document_templates": {"active"},
        "message_templates": {"active", "channel"},
        "messages": {"status", "client_id", "case_id", "channel"},
        "financial_entries": {"entry_type", "status", "client_id", "case_id", "category"},
        "message_attachments": {"message_id"},
        "tasks": {"status", "client_id", "case_id", "assigned_user_id", "priority"},
        "notifications": {"status", "channel"},
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
        "documents": "(title ILIKE %s OR file_type ILIKE %s OR file_url ILIKE %s)",
        "tasks": "(title ILIKE %s OR description ILIKE %s OR status ILIKE %s)",
        "message_templates": "(name ILIKE %s OR body ILIKE %s OR subject ILIKE %s)",
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

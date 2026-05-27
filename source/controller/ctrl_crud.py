from flask import request

from source.app import app
from source.core.system.utils import NXResult, get_session_payload
from source.logic.orb_crud import create_resource, delete_resource, get_resource_by_id, list_resource, update_resource


def _handle_list(resource_name: str):
    try:
        session_payload = get_session_payload()
    except Exception as exc:
        r = NXResult()
        r.make_error(401, "Falha na autenticacao", str(exc))
        return r.toJSON(), 401

    r = list_resource(resource_name, session_payload)
    return r.toJSON(), (200 if r.status else 400)


def _handle_create(resource_name: str):
    try:
        session_payload = get_session_payload()
    except Exception as exc:
        r = NXResult()
        r.make_error(401, "Falha na autenticacao", str(exc))
        return r.toJSON(), 401

    payload = request.get_json(silent=True) or {}
    r = create_resource(resource_name, payload, session_payload)
    return r.toJSON(), (200 if r.status else 400)


def _handle_detail(resource_name: str, record_id: str):
    try:
        session_payload = get_session_payload()
    except Exception as exc:
        r = NXResult()
        r.make_error(401, "Falha na autenticacao", str(exc))
        return r.toJSON(), 401

    r = get_resource_by_id(resource_name, record_id, session_payload)
    return r.toJSON(), (200 if r.status else 404)


def _handle_update(resource_name: str, record_id: str):
    try:
        session_payload = get_session_payload()
    except Exception as exc:
        r = NXResult()
        r.make_error(401, "Falha na autenticacao", str(exc))
        return r.toJSON(), 401

    payload = request.get_json(silent=True) or {}
    r = update_resource(resource_name, record_id, payload, session_payload)
    return r.toJSON(), (200 if r.status else 400)


def _handle_delete(resource_name: str, record_id: str):
    try:
        session_payload = get_session_payload()
    except Exception as exc:
        r = NXResult()
        r.make_error(401, "Falha na autenticacao", str(exc))
        return r.toJSON(), 401

    r = delete_resource(resource_name, record_id, session_payload)
    return r.toJSON(), (200 if r.status else 400)


def _dispatch_collection(resource_name: str):
    if request.method == "GET":
        return _handle_list(resource_name)
    return _handle_create(resource_name)


def _dispatch_item(resource_name: str, record_id: str):
    if request.method == "GET":
        return _handle_detail(resource_name, record_id)
    if request.method == "PUT":
        return _handle_update(resource_name, record_id)
    return _handle_delete(resource_name, record_id)


@app.route("/api/v1/companies", methods=["GET"])
def companies():
    return _handle_list("companies")


@app.route("/api/v1/companies/<record_id>", methods=["GET", "PUT"])
def company_item(record_id):
    return _dispatch_item("companies", record_id)


@app.route("/api/v1/users", methods=["GET", "POST"])
def users():
    return _dispatch_collection("users")


@app.route("/api/v1/users/<record_id>", methods=["GET", "PUT", "DELETE"])
def user_item(record_id):
    return _dispatch_item("users", record_id)


@app.route("/api/v1/roles", methods=["GET", "POST"])
def roles():
    return _dispatch_collection("roles")


@app.route("/api/v1/roles/<record_id>", methods=["GET", "PUT", "DELETE"])
def role_item(record_id):
    return _dispatch_item("roles", record_id)


@app.route("/api/v1/permissions", methods=["GET"])
def permissions():
    return _handle_list("permissions")


@app.route("/api/v1/role-permissions", methods=["GET", "POST"])
def role_permissions():
    return _dispatch_collection("role_permissions")


@app.route("/api/v1/role-permissions/<record_id>", methods=["GET", "PUT", "DELETE"])
def role_permission_item(record_id):
    return _dispatch_item("role_permissions", record_id)


@app.route("/api/v1/clients", methods=["GET", "POST"])
def clients():
    return _dispatch_collection("clients")


@app.route("/api/v1/clients/<record_id>", methods=["GET", "PUT", "DELETE"])
def client_item(record_id):
    return _dispatch_item("clients", record_id)


@app.route("/api/v1/lawyers", methods=["GET", "POST"])
def lawyers():
    return _dispatch_collection("lawyers")


@app.route("/api/v1/lawyers/<record_id>", methods=["GET", "PUT", "DELETE"])
def lawyer_item(record_id):
    return _dispatch_item("lawyers", record_id)


@app.route("/api/v1/cases", methods=["GET", "POST"])
def cases():
    return _dispatch_collection("cases")


@app.route("/api/v1/cases/<record_id>", methods=["GET", "PUT", "DELETE"])
def case_item(record_id):
    return _dispatch_item("cases", record_id)


@app.route("/api/v1/appointments", methods=["GET", "POST"])
def appointments():
    return _dispatch_collection("appointments")


@app.route("/api/v1/appointments/<record_id>", methods=["GET", "PUT", "DELETE"])
def appointment_item(record_id):
    return _dispatch_item("appointments", record_id)


@app.route("/api/v1/appointment-participants", methods=["GET", "POST"])
def appointment_participants():
    return _dispatch_collection("appointment_participants")


@app.route("/api/v1/appointment-participants/<record_id>", methods=["GET", "PUT", "DELETE"])
def appointment_participant_item(record_id):
    return _dispatch_item("appointment_participants", record_id)


@app.route("/api/v1/documents", methods=["GET", "POST"])
def documents():
    return _dispatch_collection("documents")


@app.route("/api/v1/documents/<record_id>", methods=["GET", "PUT", "DELETE"])
def document_item(record_id):
    return _dispatch_item("documents", record_id)


@app.route("/api/v1/document-templates", methods=["GET", "POST"])
def document_templates():
    return _dispatch_collection("document_templates")


@app.route("/api/v1/document-templates/<record_id>", methods=["GET", "PUT", "DELETE"])
def document_template_item(record_id):
    return _dispatch_item("document_templates", record_id)


@app.route("/api/v1/message-templates", methods=["GET", "POST"])
def message_templates():
    return _dispatch_collection("message_templates")


@app.route("/api/v1/message-templates/<record_id>", methods=["GET", "PUT", "DELETE"])
def message_template_item(record_id):
    return _dispatch_item("message_templates", record_id)


@app.route("/api/v1/messages", methods=["GET", "POST"])
def messages():
    return _dispatch_collection("messages")


@app.route("/api/v1/messages/<record_id>", methods=["GET", "PUT", "DELETE"])
def message_item(record_id):
    return _dispatch_item("messages", record_id)


@app.route("/api/v1/tasks", methods=["GET", "POST"])
def tasks():
    return _dispatch_collection("tasks")


@app.route("/api/v1/tasks/<record_id>", methods=["GET", "PUT", "DELETE"])
def task_item(record_id):
    return _dispatch_item("tasks", record_id)


@app.route("/api/v1/task-checklist-items", methods=["GET", "POST"])
def task_checklist_items():
    return _dispatch_collection("task_checklist_items")


@app.route("/api/v1/task-checklist-items/<record_id>", methods=["GET", "PUT", "DELETE"])
def task_checklist_item(record_id):
    return _dispatch_item("task_checklist_items", record_id)


@app.route("/api/v1/notifications", methods=["GET", "POST"])
def notifications():
    return _dispatch_collection("notifications")


@app.route("/api/v1/notifications/<record_id>", methods=["GET", "PUT", "DELETE"])
def notification_item(record_id):
    return _dispatch_item("notifications", record_id)


@app.route("/api/v1/audit", methods=["GET"])
def audit_logs():
    return _handle_list("audit_logs")

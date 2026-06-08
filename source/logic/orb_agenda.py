from __future__ import annotations

from source.core.system.database import NXDatabaseConnection
from source.core.system.utils import NXResult
from source.logic.orb_crud import create_resource, delete_resource, get_resource_by_id, update_resource


def _has_any_agenda_permission(session_payload: dict) -> bool:
    permissions = set(session_payload.get("permissions") or [])
    return bool(
        {
            "appointments.read",
            "appointments.write",
            "tasks.read",
            "tasks.write",
        }.intersection(permissions)
    )


def _can_read(resource_name: str, session_payload: dict) -> bool:
    permissions = set(session_payload.get("permissions") or [])
    permission_map = {
        "appointments": "appointments.read",
        "tasks": "tasks.read",
    }
    return permission_map[resource_name] in permissions


def _build_agenda_sql() -> str:
    return """
        SELECT
            CONCAT('appointment:', a.id::text) AS id,
            a.id::text AS source_id,
            'appointment' AS item_kind,
            a.company_id,
            a.client_id,
            a.case_id,
            a.created_by AS owner_user_id,
            a.title,
            a.notes AS description,
            a.type AS item_type,
            a.status,
            NULL::text AS priority,
            a.start_at,
            a.end_at,
            NULL::timestamp AS due_at,
            a.mode,
            a.location,
            a.created_at,
            a.updated_at
        FROM appointments a
        WHERE a.company_id = %s
          AND a.deleted_at IS NULL

        UNION ALL

        SELECT
            CONCAT('task:', t.id::text) AS id,
            t.id::text AS source_id,
            'task' AS item_kind,
            t.company_id,
            t.client_id,
            t.case_id,
            t.assigned_user_id AS owner_user_id,
            t.title,
            t.description,
            'task' AS item_type,
            t.status,
            t.priority,
            t.due_at AS start_at,
            NULL::timestamp AS end_at,
            t.due_at,
            NULL::text AS mode,
            NULL::text AS location,
            t.created_at,
            t.updated_at
        FROM tasks t
        WHERE t.company_id = %s
          AND t.deleted_at IS NULL
    """


def _apply_agenda_filters(base_sql: str, params: list, filters: dict) -> tuple[str, list]:
    sql = f"SELECT * FROM ({base_sql}) agenda_items WHERE 1=1"

    simple_filters = {
        "item_kind": "item_kind",
        "status": "status",
        "client_id": "client_id",
        "case_id": "case_id",
        "owner_user_id": "owner_user_id",
        "priority": "priority",
        "item_type": "item_type",
    }
    for filter_name, column_name in simple_filters.items():
        value = filters.get(filter_name)
        if value not in (None, ""):
            sql += f" AND {column_name} = %s"
            params.append(value)

    search = filters.get("search")
    if search:
        sql += " AND (title ILIKE %s OR COALESCE(description, '') ILIKE %s OR COALESCE(location, '') ILIKE %s)"
        term = f"%{search}%"
        params.extend([term, term, term])

    if filters.get("date_from"):
        sql += " AND COALESCE(start_at, due_at) >= %s"
        params.append(filters["date_from"])

    if filters.get("date_to"):
        sql += " AND COALESCE(start_at, due_at) <= %s"
        params.append(filters["date_to"])

    sql += " ORDER BY COALESCE(start_at, due_at) ASC NULLS LAST, created_at DESC"

    limit = filters.get("limit")
    if limit not in (None, ""):
        sql += " LIMIT %s"
        params.append(int(limit))

    return sql, params


def _normalize_agenda_item(row: dict) -> dict:
    item = dict(row)
    item["kind"] = item["item_kind"]
    item["all_day"] = False
    item["display_date"] = item.get("start_at") or item.get("due_at")
    return item


def list_agenda_items(session_payload: dict, filters: dict) -> NXResult:
    r = NXResult()
    if not _has_any_agenda_permission(session_payload):
        r.make_error(403, "Permissao insuficiente para consultar agenda")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        base_sql = _build_agenda_sql()
        params = [session_payload["company_id"], session_payload["company_id"]]
        sql, params = _apply_agenda_filters(base_sql, params, filters)
        nx.xp_nx.execute(sql, tuple(params))
        rows = nx.xp_nx.fetchall()
        items = [_normalize_agenda_item(dict(row)) for row in rows if _can_read(dict(row)["item_kind"] + "s", session_payload)]
        r.status = True
        r.message = "Itens da agenda carregados com sucesso"
        r.data = items
    except Exception as exc:
        r.make_error(0, "Erro ao consultar itens da agenda", str(exc))
    finally:
        nx.stop()

    return r


def _resolve_resource_kind(record_id: str, preferred_kind: str | None = None) -> tuple[str | None, str]:
    normalized = (preferred_kind or "").strip().lower()
    if normalized in {"appointment", "appointments"}:
        return "appointments", record_id.replace("appointment:", "", 1)
    if normalized in {"task", "tasks"}:
        return "tasks", record_id.replace("task:", "", 1)
    if record_id.startswith("appointment:"):
        return "appointments", record_id.split(":", 1)[1]
    if record_id.startswith("task:"):
        return "tasks", record_id.split(":", 1)[1]
    return None, record_id


def get_agenda_item(record_id: str, session_payload: dict, preferred_kind: str | None = None) -> NXResult:
    resource_name, source_id = _resolve_resource_kind(record_id, preferred_kind)
    if resource_name:
        detail = get_resource_by_id(resource_name, source_id, session_payload)
        if detail.status:
            payload = dict(detail.data)
            payload["source_id"] = str(payload["id"])
            payload["id"] = f"{resource_name[:-1]}:{payload['source_id']}"
            payload["item_kind"] = resource_name[:-1]
            payload["kind"] = payload["item_kind"]
            detail.data = payload
            detail.message = "Item da agenda carregado com sucesso"
        return detail

    for fallback in ("appointments", "tasks"):
        detail = get_resource_by_id(fallback, source_id, session_payload)
        if detail.status:
            payload = dict(detail.data)
            payload["source_id"] = str(payload["id"])
            payload["id"] = f"{fallback[:-1]}:{payload['source_id']}"
            payload["item_kind"] = fallback[:-1]
            payload["kind"] = payload["item_kind"]
            detail.data = payload
            detail.message = "Item da agenda carregado com sucesso"
            return detail

    r = NXResult()
    r.make_error(404, "Item da agenda nao localizado")
    return r


def _infer_target_resource(payload: dict) -> str:
    item_kind = (payload.get("item_kind") or payload.get("kind") or "").strip().lower()
    if item_kind in {"appointment", "appointments"}:
        return "appointments"
    if item_kind in {"task", "tasks"}:
        return "tasks"

    if payload.get("start_at") or payload.get("end_at") or payload.get("mode") or payload.get("location"):
        return "appointments"
    return "tasks"


def create_agenda_item(payload: dict, session_payload: dict) -> NXResult:
    resource_name = _infer_target_resource(payload)
    result = create_resource(resource_name, payload, session_payload)
    if result.status and isinstance(result.data, dict) and result.data.get("id"):
        source_id = str(result.data["id"])
        result.data = {
            "id": f"{resource_name[:-1]}:{source_id}",
            "source_id": source_id,
            "item_kind": resource_name[:-1],
        }
        result.message = "Item da agenda cadastrado com sucesso"
    return result


def update_agenda_item(record_id: str, payload: dict, session_payload: dict, preferred_kind: str | None = None) -> NXResult:
    resource_name, source_id = _resolve_resource_kind(record_id, preferred_kind or payload.get("item_kind") or payload.get("kind"))
    if not resource_name:
        resource_name = _infer_target_resource(payload)
    result = update_resource(resource_name, source_id, payload, session_payload)
    if result.status and isinstance(result.data, dict) and result.data.get("id"):
        source_id = str(result.data["id"])
        result.data = {
            "id": f"{resource_name[:-1]}:{source_id}",
            "source_id": source_id,
            "item_kind": resource_name[:-1],
        }
        result.message = "Item da agenda atualizado com sucesso"
    return result


def delete_agenda_item(record_id: str, session_payload: dict, preferred_kind: str | None = None) -> NXResult:
    resource_name, source_id = _resolve_resource_kind(record_id, preferred_kind)
    if not resource_name:
        r = NXResult()
        r.make_error(400, "Identificador do item da agenda invalido", "Use prefixo appointment: ou task:")
        return r

    result = delete_resource(resource_name, source_id, session_payload)
    if result.status:
        result.data = {
            "id": record_id,
            "source_id": source_id,
            "item_kind": resource_name[:-1],
        }
        result.message = "Item da agenda removido com sucesso"
    return result

import re

from source.core.system.database import NXDatabaseConnection
from source.core.system.utils import NXResult
from source.logic.orb_audit import register_audit_log


PLACEHOLDER_PATTERN = re.compile(r"{{\s*([a-zA-Z0-9_.-]+)\s*}}")


def _flatten_payload(prefix: str, value, acc: dict) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            name = f"{prefix}.{key}" if prefix else key
            _flatten_payload(name, nested, acc)
    else:
        acc[prefix] = "" if value is None else str(value)


def _replace_placeholders(template_body: str, context: dict) -> str:
    flat = {}
    _flatten_payload("", context, flat)

    def _resolver(match):
        return flat.get(match.group(1), "")

    return PLACEHOLDER_PATTERN.sub(_resolver, template_body)


def generate_document(session_payload: dict, payload: dict) -> NXResult:
    r = NXResult()
    template_id = payload.get("template_id")
    context = payload.get("context") or {}
    if not template_id:
        r.make_error(0, "template_id e obrigatorio")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            """
            SELECT id, name, category, file_type, template_body, variables
            FROM document_templates
            WHERE id = %s AND company_id = %s AND deleted_at IS NULL
            """,
            (template_id, session_payload["company_id"]),
        )
        template = nx.xp_nx.fetchone()
        if not template:
            r.make_error(404, "Template de documento nao localizado")
            return r

        rendered_body = _replace_placeholders(template["template_body"], context)
        register_audit_log(
            session_payload["company_id"],
            session_payload.get("user_id"),
            "document_templates",
            str(template["id"]),
            "generate",
            None,
            {"context_keys": list(context.keys())},
        )
        r.status = True
        r.message = "Documento gerado com sucesso"
        r.data = {
            "template_id": str(template["id"]),
            "template_name": template["name"],
            "category": template["category"],
            "file_type": template["file_type"],
            "content": rendered_body,
        }
    except Exception as exc:
        r.make_error(0, "Erro ao gerar documento", str(exc))
    finally:
        nx.stop()

    return r


def send_message_from_template(session_payload: dict, payload: dict) -> NXResult:
    r = NXResult()
    template_id = payload.get("template_id")
    recipient = payload.get("recipient")
    context = payload.get("context") or {}
    if not template_id or not recipient:
        r.make_error(0, "template_id e recipient sao obrigatorios")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            """
            SELECT id, name, channel, subject, body
            FROM message_templates
            WHERE id = %s AND company_id = %s
            """,
            (template_id, session_payload["company_id"]),
        )
        template = nx.xp_nx.fetchone()
        if not template:
            r.make_error(404, "Template de mensagem nao localizado")
            return r

        rendered_subject = _replace_placeholders(template["subject"] or "", context)
        rendered_body = _replace_placeholders(template["body"], context)
        nx.xp_nx.execute(
            """
            INSERT INTO messages (company_id, client_id, case_id, template_id, channel, recipient, subject, body, status, sent_at, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
            RETURNING id
            """,
            (
                session_payload["company_id"],
                payload.get("client_id"),
                payload.get("case_id"),
                template["id"],
                payload.get("channel") or template["channel"],
                recipient,
                rendered_subject,
                rendered_body,
                "sent",
                session_payload.get("user_id"),
            ),
        )
        message = nx.xp_nx.fetchone()
        nx.conn_nx.commit()
        register_audit_log(
            session_payload["company_id"],
            session_payload.get("user_id"),
            "messages",
            str(message["id"]),
            "send",
            None,
            {"template_id": str(template["id"]), "recipient": recipient},
        )
        r.status = True
        r.message = "Mensagem gerada e registrada com sucesso"
        r.data = {
            "message_id": str(message["id"]),
            "channel": payload.get("channel") or template["channel"],
            "recipient": recipient,
            "subject": rendered_subject,
            "body": rendered_body,
            "status": "sent",
        }
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao enviar mensagem por template", str(exc))
    finally:
        nx.stop()

    return r

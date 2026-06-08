from source.core.system.database import NXDatabaseConnection
from source.core.system.utils import NXResult
from source.logic.orb_audit import register_audit_log


def get_public_company_profile(company_code: str) -> NXResult:
    r = NXResult()
    code = (company_code or "").strip().lower()
    if not code:
        r.make_error(0, "company_code obrigatorio")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            """
            SELECT c.id, c.code, c.name, c.email, c.phone, c.logo_url, c.status,
                   cs.locale, cs.timezone, cs.settings
            FROM companies c
            LEFT JOIN company_settings cs ON cs.company_id = c.id
            WHERE LOWER(c.code) = %s
              AND c.deleted_at IS NULL
              AND c.status = 'active'
            LIMIT 1
            """,
            (code,),
        )
        row = nx.xp_nx.fetchone()
        if not row:
            r.make_error(404, "Escritorio nao localizado")
            return r

        r.status = True
        r.message = "Perfil publico carregado com sucesso"
        r.data = dict(row)
    except Exception as exc:
        r.make_error(0, "Erro ao carregar perfil publico", str(exc))
    finally:
        nx.stop()

    return r


def create_public_lead(payload: dict) -> NXResult:
    r = NXResult()
    company_code = (payload.get("company_code") or "").strip().lower()
    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip()
    phone = (payload.get("phone") or "").strip()

    if not company_code or not name:
        r.make_error(0, "company_code e name sao obrigatorios")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            """
            SELECT id, name
            FROM companies
            WHERE LOWER(code) = %s
              AND deleted_at IS NULL
              AND status = 'active'
            LIMIT 1
            """,
            (company_code,),
        )
        company = nx.xp_nx.fetchone()
        if not company:
            r.make_error(404, "Escritorio nao localizado")
            return r

        origin = (payload.get("origin") or "captura_publica").strip()
        notes_parts = [
            "Lead capturado publicamente pelo site do escritorio.",
            f"Origem: {origin}.",
        ]
        if payload.get("notes"):
            notes_parts.append(str(payload["notes"]).strip())

        nx.xp_nx.execute(
            """
            INSERT INTO clients (
                company_id, name, document, email, phone, notes, status, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id, name, status, created_at
            """,
            (
                company["id"],
                name,
                payload.get("document"),
                email or None,
                phone or None,
                " ".join([part for part in notes_parts if part]),
                payload.get("status") or "lead",
            ),
        )
        lead = nx.xp_nx.fetchone()
        nx.conn_nx.commit()

        register_audit_log(
            str(company["id"]),
            None,
            "clients",
            str(lead["id"]),
            "public_lead_create",
            None,
            {
                "name": name,
                "email": email,
                "phone": phone,
                "origin": origin,
            },
        )

        r.status = True
        r.message = "Lead enviado com sucesso"
        r.data = {
            "id": str(lead["id"]),
            "company_id": str(company["id"]),
            "company_name": company["name"],
            "status": lead["status"],
        }
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao registrar lead publico", str(exc))
    finally:
        nx.stop()

    return r


def create_client_portal_session(payload: dict) -> NXResult:
    r = NXResult()
    company_code = (payload.get("company_code") or "").strip().lower()
    email = (payload.get("email") or "").strip().lower()
    document = (payload.get("document") or "").strip()
    phone = (payload.get("phone") or "").strip()

    if not company_code:
        r.make_error(0, "company_code obrigatorio")
        return r

    if not email and not document and not phone:
        r.make_error(0, "Informe email, documento ou telefone para acessar o portal")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            """
            SELECT c.id, c.name
            FROM companies c
            WHERE LOWER(c.code) = %s
              AND c.deleted_at IS NULL
              AND c.status = 'active'
            LIMIT 1
            """,
            (company_code,),
        )
        company = nx.xp_nx.fetchone()
        if not company:
            r.make_error(404, "Escritorio nao localizado")
            return r

        conditions = []
        params = [company["id"]]
        if email:
            conditions.append("LOWER(cl.email) = %s")
            params.append(email)
        if document:
            conditions.append("cl.document = %s")
            params.append(document)
        if phone:
            conditions.append("cl.phone = %s")
            params.append(phone)

        where_clause = " OR ".join(conditions)
        nx.xp_nx.execute(
            f"""
            SELECT cl.id, cl.name, cl.document, cl.email, cl.phone, cl.notes, cl.status, cl.created_at
            FROM clients cl
            WHERE cl.company_id = %s
              AND cl.deleted_at IS NULL
              AND ({where_clause})
            ORDER BY cl.created_at DESC
            LIMIT 1
            """,
            tuple(params),
        )
        client = nx.xp_nx.fetchone()
        if not client:
            r.make_error(404, "Cliente nao localizado para os dados informados")
            return r

        client_id = client["id"]
        company_id = company["id"]

        nx.xp_nx.execute(
            """
            SELECT id, case_number, title, area, court, district, court_branch, phase, status, created_at
            FROM cases
            WHERE company_id = %s AND client_id = %s AND deleted_at IS NULL
            ORDER BY created_at DESC
            """,
            (company_id, client_id),
        )
        cases = [dict(row) for row in nx.xp_nx.fetchall()]

        nx.xp_nx.execute(
            """
            SELECT id, title, file_type, file_url, status, created_at, case_id
            FROM documents
            WHERE company_id = %s AND client_id = %s AND deleted_at IS NULL
            ORDER BY created_at DESC
            """,
            (company_id, client_id),
        )
        documents = [dict(row) for row in nx.xp_nx.fetchall()]

        nx.xp_nx.execute(
            """
            SELECT id, channel, subject, body, status, sent_at, created_at, case_id
            FROM messages
            WHERE company_id = %s AND client_id = %s
            ORDER BY COALESCE(sent_at, created_at) DESC
            """,
            (company_id, client_id),
        )
        messages = [dict(row) for row in nx.xp_nx.fetchall()]

        nx.xp_nx.execute(
            """
            SELECT
              'appointment' AS item_kind,
              id,
              title,
              type,
              status,
              start_at AS date_ref,
              location,
              mode,
              case_id
            FROM appointments
            WHERE company_id = %s AND client_id = %s AND deleted_at IS NULL
            UNION ALL
            SELECT
              'task' AS item_kind,
              id,
              title,
              priority AS type,
              status,
              due_at AS date_ref,
              NULL AS location,
              NULL AS mode,
              case_id
            FROM tasks
            WHERE company_id = %s AND client_id = %s AND deleted_at IS NULL
            ORDER BY date_ref DESC NULLS LAST
            """,
            (company_id, client_id, company_id, client_id),
        )
        agenda_items = [dict(row) for row in nx.xp_nx.fetchall()]

        active_cases = sum(1 for row in cases if str(row.get("status") or "").lower() in {"open", "active", "in_progress"})
        open_documents = sum(1 for row in documents if str(row.get("status") or "").lower() not in {"archived", "cancelled"})
        upcoming_items = [
            row for row in agenda_items
            if row.get("date_ref")
        ]
        next_item = upcoming_items[0] if upcoming_items else None
        latest_message = messages[0] if messages else None
        portal_summary = (
            f"Cliente com {len(cases)} processo(s), {active_cases} ativo(s), "
            f"{len(documents)} documento(s) e {len(messages)} comunicação(ões) registrada(s)."
        )

        r.status = True
        r.message = "Portal do cliente carregado com sucesso"
        r.data = {
            "company": {"id": str(company["id"]), "name": company["name"], "code": company_code},
            "client": dict(client),
            "summary": {
                "executive_summary": portal_summary,
                "active_cases": active_cases,
                "documents_available": open_documents,
                "messages_count": len(messages),
                "agenda_count": len(agenda_items),
                "next_item": next_item,
                "latest_message": latest_message,
            },
            "cases": cases,
            "documents": documents,
            "messages": messages,
            "agenda_items": agenda_items,
        }
    except Exception as exc:
        r.make_error(0, "Erro ao carregar portal do cliente", str(exc))
    finally:
        nx.stop()

    return r


def get_public_signature_request(token: str) -> NXResult:
    r = NXResult()
    access_token = (token or "").strip()
    if not access_token:
        r.make_error(0, "token obrigatorio")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            """
            SELECT sr.id, sr.document_id, sr.signer_name, sr.signer_email, sr.signer_document, sr.signer_role,
                   sr.status, sr.sent_at, sr.viewed_at, sr.signed_at, sr.cancelled_at, sr.notes,
                   d.title AS document_title, d.file_url, d.file_type,
                   c.name AS company_name, c.code AS company_code, c.logo_url
            FROM document_signature_requests sr
            JOIN documents d ON d.id = sr.document_id
            JOIN companies c ON c.id = sr.company_id
            WHERE sr.access_token::text = %s
              AND sr.deleted_at IS NULL
              AND d.deleted_at IS NULL
              AND c.deleted_at IS NULL
            LIMIT 1
            """,
            (access_token,),
        )
        row = nx.xp_nx.fetchone()
        if not row:
            r.make_error(404, "Solicitacao de assinatura nao localizada")
            return r

        current_status = str(row["status"] or "").lower()
        if current_status in {"pending", "sent"}:
            nx.xp_nx.execute(
                """
                UPDATE document_signature_requests
                SET status = 'viewed',
                    viewed_at = COALESCE(viewed_at, NOW()),
                    updated_at = NOW()
                WHERE id = %s
                """,
                (row["id"],),
            )
            nx.conn_nx.commit()
            row["status"] = "viewed"
            row["viewed_at"] = row["viewed_at"] or "NOW"

        r.status = True
        r.message = "Solicitacao de assinatura carregada com sucesso"
        r.data = dict(row)
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao carregar solicitacao de assinatura", str(exc))
    finally:
        nx.stop()

    return r


def sign_public_signature_request(token: str, payload: dict) -> NXResult:
    r = NXResult()
    access_token = (token or "").strip()
    signer_name = (payload.get("signer_name") or "").strip()
    signer_document = (payload.get("signer_document") or "").strip()

    if not access_token:
        r.make_error(0, "token obrigatorio")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            """
            SELECT id, company_id, document_id, signer_name, status
            FROM document_signature_requests
            WHERE access_token::text = %s
              AND deleted_at IS NULL
            LIMIT 1
            """,
            (access_token,),
        )
        row = nx.xp_nx.fetchone()
        if not row:
            r.make_error(404, "Solicitacao de assinatura nao localizada")
            return r

        current_status = str(row["status"] or "").lower()
        if current_status == "signed":
            r.make_error(400, "Este documento ja foi assinado")
            return r
        if current_status == "cancelled":
            r.make_error(400, "Esta solicitacao foi cancelada")
            return r

        final_signer_name = signer_name or row["signer_name"]

        nx.xp_nx.execute(
            """
            UPDATE document_signature_requests
            SET signer_name = %s,
                signer_document = COALESCE(NULLIF(%s, ''), signer_document),
                status = 'signed',
                signed_at = NOW(),
                updated_at = NOW()
            WHERE id = %s
            RETURNING id, status, signed_at
            """,
            (final_signer_name, signer_document, row["id"]),
        )
        signed = nx.xp_nx.fetchone()
        nx.conn_nx.commit()

        register_audit_log(
            str(row["company_id"]),
            None,
            "document_signature_requests",
            str(row["id"]),
            "public_sign",
            None,
            {
                "document_id": str(row["document_id"]),
                "signer_name": final_signer_name,
                "signer_document": signer_document,
            },
        )

        r.status = True
        r.message = "Documento assinado com sucesso"
        r.data = {
            "id": str(signed["id"]),
            "status": signed["status"],
            "signed_at": signed["signed_at"],
        }
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao registrar assinatura", str(exc))
    finally:
        nx.stop()

    return r

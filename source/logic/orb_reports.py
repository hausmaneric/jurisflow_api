from flask import request

from source.core.system.database import NXDatabaseConnection
from source.core.system.utils import NXResult
from source.data.sql.sql_reports import SQL_TIMELINE
import re


def operational_summary(session_payload: dict) -> NXResult:
    r = NXResult()
    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        company_id = session_payload["company_id"]
        metrics = {}
        queries = {
            "clients": "SELECT COUNT(*) AS total FROM clients WHERE company_id = %s AND deleted_at IS NULL",
            "lawyers": "SELECT COUNT(*) AS total FROM lawyers WHERE company_id = %s AND deleted_at IS NULL",
            "cases_open": "SELECT COUNT(*) AS total FROM cases WHERE company_id = %s AND deleted_at IS NULL AND status = 'open'",
            "appointments_upcoming": "SELECT COUNT(*) AS total FROM appointments WHERE company_id = %s AND deleted_at IS NULL AND start_at >= NOW()",
            "tasks_open": "SELECT COUNT(*) AS total FROM tasks WHERE company_id = %s AND deleted_at IS NULL AND status IN ('open', 'pending')",
            "documents": "SELECT COUNT(*) AS total FROM documents WHERE company_id = %s AND deleted_at IS NULL",
            "notifications_pending": "SELECT COUNT(*) AS total FROM notifications WHERE company_id = %s AND status = 'pending'",
        }
        for key, sql in queries.items():
            nx.xp_nx.execute(sql, (company_id,))
            metrics[key] = nx.xp_nx.fetchone()["total"]

        r.status = True
        r.message = "Resumo operacional carregado com sucesso"
        r.data = metrics
    except Exception as exc:
        r.make_error(0, "Erro ao carregar resumo operacional", str(exc))
    finally:
        nx.stop()

    return r


def operational_timeline(session_payload: dict) -> NXResult:
    r = NXResult()
    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        company_id = session_payload["company_id"]
        nx.xp_nx.execute(SQL_TIMELINE, (company_id, company_id, company_id))
        rows = nx.xp_nx.fetchall()
        r.status = True
        r.message = "Timeline operacional carregada com sucesso"
        r.data = [dict(row) for row in rows]
    except Exception as exc:
        r.make_error(0, "Erro ao carregar timeline operacional", str(exc))
    finally:
        nx.stop()

    return r


def operational_bi(session_payload: dict) -> NXResult:
    r = NXResult()
    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        company_id = session_payload["company_id"]

        nx.xp_nx.execute(
            """
            SELECT COALESCE(area, 'Nao informada') AS label, COUNT(*) AS total
            FROM cases
            WHERE company_id = %s AND deleted_at IS NULL
            GROUP BY COALESCE(area, 'Nao informada')
            ORDER BY total DESC, label ASC
            """,
            (company_id,),
        )
        cases_by_area = [dict(row) for row in nx.xp_nx.fetchall()]

        nx.xp_nx.execute(
            """
            SELECT COALESCE(status, 'sem_status') AS label, COUNT(*) AS total
            FROM cases
            WHERE company_id = %s AND deleted_at IS NULL
            GROUP BY COALESCE(status, 'sem_status')
            ORDER BY total DESC, label ASC
            """,
            (company_id,),
        )
        cases_by_status = [dict(row) for row in nx.xp_nx.fetchall()]

        nx.xp_nx.execute(
            """
            SELECT COALESCE(type, 'compromisso') AS label, COUNT(*) AS total
            FROM appointments
            WHERE company_id = %s AND deleted_at IS NULL
            GROUP BY COALESCE(type, 'compromisso')
            ORDER BY total DESC, label ASC
            """,
            (company_id,),
        )
        agenda_by_type = [dict(row) for row in nx.xp_nx.fetchall()]

        nx.xp_nx.execute(
            """
            SELECT COALESCE(u.name, 'Equipe') AS label, COUNT(*) AS total
            FROM tasks t
            LEFT JOIN users u ON u.id = t.assigned_user_id
            WHERE t.company_id = %s AND t.deleted_at IS NULL
            GROUP BY COALESCE(u.name, 'Equipe')
            ORDER BY total DESC, label ASC
            LIMIT 10
            """,
            (company_id,),
        )
        productivity = [dict(row) for row in nx.xp_nx.fetchall()]

        nx.xp_nx.execute(
            """
            SELECT COALESCE(c.name, 'Cliente nao informado') AS label, COUNT(cs.id) AS total
            FROM cases cs
            LEFT JOIN clients c ON c.id = cs.client_id
            WHERE cs.company_id = %s AND cs.deleted_at IS NULL
            GROUP BY COALESCE(c.name, 'Cliente nao informado')
            ORDER BY total DESC, label ASC
            LIMIT 5
            """,
            (company_id,),
        )
        top_clients_by_cases = [dict(row) for row in nx.xp_nx.fetchall()]

        r.status = True
        r.message = "BI juridico carregado com sucesso"
        r.data = {
          "cases_by_area": cases_by_area,
          "cases_by_status": cases_by_status,
          "agenda_by_type": agenda_by_type,
          "productivity": productivity,
          "top_clients_by_cases": top_clients_by_cases,
        }
    except Exception as exc:
        r.make_error(0, "Erro ao carregar BI juridico", str(exc))
    finally:
        nx.stop()

    return r


def financial_summary(session_payload: dict) -> NXResult:
    r = NXResult()
    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        company_id = session_payload["company_id"]
        filters = ["company_id = %s", "deleted_at IS NULL"]
        params: list = [company_id]

        entry_type = (request.args.get("entry_type") or "").strip().lower()
        status = (request.args.get("status") or "").strip().lower()
        category = (request.args.get("category") or "").strip()
        date_from = (request.args.get("date_from") or "").strip()
        date_to = (request.args.get("date_to") or "").strip()

        if entry_type:
            filters.append("LOWER(entry_type) = %s")
            params.append(entry_type)
        if status:
            filters.append("LOWER(status) = %s")
            params.append(status)
        if category:
            filters.append("category = %s")
            params.append(category)
        if date_from:
            filters.append("entry_date >= %s")
            params.append(date_from)
        if date_to:
            filters.append("entry_date <= %s")
            params.append(date_to)

        where_clause = " AND ".join(filters)

        nx.xp_nx.execute(
            f"""
            SELECT
                COUNT(*) AS total_entries,
                COUNT(*) FILTER (WHERE LOWER(entry_type) = 'income') AS income_entries,
                COUNT(*) FILTER (WHERE LOWER(entry_type) = 'expense') AS expense_entries,
                COUNT(*) FILTER (WHERE LOWER(status) = 'pending') AS pending_entries,
                COUNT(*) FILTER (WHERE LOWER(status) = 'overdue') AS overdue_entries,
                COALESCE(SUM(CASE WHEN LOWER(entry_type) = 'income' THEN amount ELSE 0 END), 0) AS total_income,
                COALESCE(SUM(CASE WHEN LOWER(entry_type) = 'expense' THEN amount ELSE 0 END), 0) AS total_expense,
                COALESCE(SUM(CASE
                    WHEN LOWER(entry_type) = 'income' THEN amount
                    WHEN LOWER(entry_type) = 'expense' THEN -amount
                    ELSE 0
                END), 0) AS balance
            FROM financial_entries
            WHERE {where_clause}
            """,
            tuple(params),
        )
        totals_row = dict(nx.xp_nx.fetchone() or {})

        nx.xp_nx.execute(
            f"""
            SELECT category AS label, COUNT(*) AS total_entries, COALESCE(SUM(amount), 0) AS total_amount
            FROM financial_entries
            WHERE {where_clause}
            GROUP BY category
            ORDER BY total_amount DESC, label ASC
            LIMIT 8
            """,
            tuple(params),
        )
        by_category = [dict(row) for row in nx.xp_nx.fetchall()]

        nx.xp_nx.execute(
            f"""
            SELECT COALESCE(account_label, 'Conta principal') AS label,
                   COUNT(*) AS total_entries,
                   COALESCE(SUM(CASE
                       WHEN LOWER(entry_type) = 'income' THEN amount
                       WHEN LOWER(entry_type) = 'expense' THEN -amount
                       ELSE 0
                   END), 0) AS balance
            FROM financial_entries
            WHERE {where_clause}
            GROUP BY COALESCE(account_label, 'Conta principal')
            ORDER BY ABS(COALESCE(SUM(CASE
                       WHEN LOWER(entry_type) = 'income' THEN amount
                       WHEN LOWER(entry_type) = 'expense' THEN -amount
                       ELSE 0
                   END), 0)) DESC, label ASC
            LIMIT 6
            """,
            tuple(params),
        )
        by_account = [dict(row) for row in nx.xp_nx.fetchall()]

        total_income = float(totals_row.get("total_income") or 0)
        total_expense = float(totals_row.get("total_expense") or 0)
        balance = float(totals_row.get("balance") or 0)
        pending_entries = int(totals_row.get("pending_entries") or 0)
        overdue_entries = int(totals_row.get("overdue_entries") or 0)

        health_score = 92
        if overdue_entries:
            health_score -= min(overdue_entries * 15, 30)
        if pending_entries >= 4:
            health_score -= 15
        elif pending_entries >= 2:
            health_score -= 8
        if total_income and total_expense > total_income * 0.85:
            health_score -= 10
        if balance < 0:
            health_score -= 20
        health_score = max(25, min(99, health_score))

        if balance < 0 or overdue_entries >= 2:
            risk_level = "alto"
        elif pending_entries >= 2 or (total_income and balance / total_income < 0.2):
            risk_level = "medio"
        else:
            risk_level = "baixo"

        r.status = True
        r.message = "Resumo financeiro carregado com sucesso"
        r.data = {
            "totals": totals_row,
            "health_score": health_score,
            "risk_level": risk_level,
            "by_category": by_category,
            "by_account": by_account,
        }
    except Exception as exc:
        r.make_error(0, "Erro ao carregar resumo financeiro", str(exc))
    finally:
        nx.stop()

    return r


def case_ai_insights(case_id: str, session_payload: dict) -> NXResult:
    r = NXResult()
    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        company_id = session_payload["company_id"]

        nx.xp_nx.execute(
            """
            SELECT cs.id, cs.case_number, cs.title, cs.area, cs.court, cs.phase, cs.status, cs.notes,
                   cl.name AS client_name
            FROM cases cs
            LEFT JOIN clients cl ON cl.id = cs.client_id
            WHERE cs.company_id = %s AND cs.id = %s AND cs.deleted_at IS NULL
            LIMIT 1
            """,
            (company_id, case_id),
        )
        case_row = nx.xp_nx.fetchone()
        if not case_row:
            r.make_error(404, "Processo nao localizado")
            return r

        nx.xp_nx.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE deleted_at IS NULL) AS total_tasks,
                COUNT(*) FILTER (WHERE deleted_at IS NULL AND status IN ('open', 'pending', 'in_progress')) AS open_tasks,
                COUNT(*) FILTER (WHERE deleted_at IS NULL AND due_at IS NOT NULL AND due_at < NOW() AND status NOT IN ('done', 'completed')) AS overdue_tasks
            FROM tasks
            WHERE company_id = %s AND case_id = %s
            """,
            (company_id, case_id),
        )
        tasks_row = nx.xp_nx.fetchone()

        nx.xp_nx.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE deleted_at IS NULL) AS total_appointments,
                COUNT(*) FILTER (WHERE deleted_at IS NULL AND start_at >= NOW()) AS upcoming_appointments,
                MIN(start_at) FILTER (WHERE deleted_at IS NULL AND start_at >= NOW()) AS next_appointment_at
            FROM appointments
            WHERE company_id = %s AND case_id = %s
            """,
            (company_id, case_id),
        )
        appointments_row = nx.xp_nx.fetchone()

        nx.xp_nx.execute(
            """
            SELECT COUNT(*) AS total_documents
            FROM documents
            WHERE company_id = %s AND case_id = %s AND deleted_at IS NULL
            """,
            (company_id, case_id),
        )
        documents_row = nx.xp_nx.fetchone()

        nx.xp_nx.execute(
            """
            SELECT COUNT(*) AS total_messages
            FROM messages
            WHERE company_id = %s AND case_id = %s
            """,
            (company_id, case_id),
        )
        messages_row = nx.xp_nx.fetchone()

        overdue_tasks = int(tasks_row["overdue_tasks"] or 0)
        open_tasks = int(tasks_row["open_tasks"] or 0)
        upcoming_appointments = int(appointments_row["upcoming_appointments"] or 0)
        total_documents = int(documents_row["total_documents"] or 0)
        total_messages = int(messages_row["total_messages"] or 0)

        health_score = 90
        if overdue_tasks:
            health_score -= min(overdue_tasks * 12, 36)
        if open_tasks >= 5:
            health_score -= 10
        if not total_documents:
            health_score -= 12
        if not upcoming_appointments:
            health_score -= 8
        health_score = max(25, min(98, health_score))

        if overdue_tasks >= 2:
            risk_level = "alto"
        elif overdue_tasks == 1 or open_tasks >= 4:
            risk_level = "medio"
        else:
            risk_level = "baixo"

        summary_parts = [
            f"Processo {case_row['case_number'] or 'sem numero'} em {case_row['phase'] or 'fase nao informada'}",
            f"na area {case_row['area'] or 'juridica nao informada'}",
        ]
        if case_row.get("client_name"):
            summary_parts.append(f"do cliente {case_row['client_name']}")
        summary = ", ".join(summary_parts) + "."

        next_actions = []
        if overdue_tasks:
            next_actions.append("Priorizar imediatamente as tarefas vencidas vinculadas a este processo.")
        if open_tasks and not overdue_tasks:
            next_actions.append("Distribuir e acompanhar os itens da agenda ainda pendentes.")
        if not upcoming_appointments:
            next_actions.append("Avaliar se o processo precisa de novo compromisso, prazo ou audiência na agenda.")
        if not total_documents:
            next_actions.append("Anexar documentação inicial ou complementar para melhorar o histórico do caso.")
        if total_messages < 2:
            next_actions.append("Registrar comunicação com o cliente para manter a trilha operacional atualizada.")
        if not next_actions:
            next_actions.append("Manter o acompanhamento atual e revisar o processo após a próxima movimentação.")

        communication_suggestion = (
            f"Olá {case_row.get('client_name') or 'cliente'}, "
            f"seguimos acompanhando o processo {case_row.get('case_number') or ''}. "
            "Estamos revisando os próximos passos operacionais e entraremos em contato em caso de nova movimentação."
        ).strip()

        document_suggestion = (
            "Checklist de acompanhamento processual"
            if overdue_tasks or open_tasks
            else "Resumo executivo do processo"
        )

        r.status = True
        r.message = "Insights juridicos carregados com sucesso"
        r.data = {
            "case_id": str(case_row["id"]),
            "summary": summary,
            "health_score": health_score,
            "risk_level": risk_level,
            "open_tasks": open_tasks,
            "overdue_tasks": overdue_tasks,
            "upcoming_appointments": upcoming_appointments,
            "documents_count": total_documents,
            "messages_count": total_messages,
            "next_appointment_at": appointments_row["next_appointment_at"],
            "next_actions": next_actions,
            "communication_suggestion": communication_suggestion,
            "document_suggestion": document_suggestion,
        }
    except Exception as exc:
        r.make_error(0, "Erro ao carregar insights juridicos", str(exc))
    finally:
        nx.stop()

    return r


def document_ai_insights(document_id: str, session_payload: dict) -> NXResult:
    r = NXResult()
    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        company_id = session_payload["company_id"]

        nx.xp_nx.execute(
            """
            SELECT d.id, d.title, d.document_type, d.file_type, d.status, d.notes,
                   d.client_id, d.case_id,
                   c.name AS client_name,
                   cs.case_number
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            LEFT JOIN cases cs ON cs.id = d.case_id
            WHERE d.company_id = %s AND d.id = %s AND d.deleted_at IS NULL
            LIMIT 1
            """,
            (company_id, document_id),
        )
        document_row = nx.xp_nx.fetchone()
        if not document_row:
            r.make_error(404, "Documento nao localizado")
            return r

        nx.xp_nx.execute(
            """
            SELECT extracted_text, reviewed_text, confidence_score, status, engine, created_at, updated_at
            FROM document_ocr_results
            WHERE company_id = %s AND document_id = %s AND deleted_at IS NULL
            ORDER BY updated_at DESC NULLS LAST, created_at DESC
            LIMIT 1
            """,
            (company_id, document_id),
        )
        ocr_row = nx.xp_nx.fetchone()

        text_source = ""
        if ocr_row:
            text_source = (ocr_row.get("reviewed_text") or ocr_row.get("extracted_text") or "").strip()
        notes = (document_row.get("notes") or "").strip()
        full_text = (text_source or notes or "").strip()

        normalized_text = re.sub(r"\s+", " ", full_text).strip()
        summary = normalized_text[:320] + ("..." if len(normalized_text) > 320 else "")
        if not summary:
            summary = "Documento sem texto suficiente para gerar resumo automático."

        keywords_source = re.findall(r"[A-Za-zÀ-ÿ0-9]{4,}", normalized_text.lower())
        ignore_words = {
            "para", "este", "essa", "com", "como", "mais", "menos", "pela", "pelo",
            "documento", "cliente", "processo", "sobre", "entre", "dados", "caso",
        }
        keyword_counts = {}
        for token in keywords_source:
            if token in ignore_words:
                continue
            keyword_counts[token] = keyword_counts.get(token, 0) + 1
        keywords = [row[0] for row in sorted(keyword_counts.items(), key=lambda item: (-item[1], item[0]))[:6]]

        confidence = float(ocr_row.get("confidence_score") or 0) if ocr_row else 0.0
        if confidence >= 0.9:
            extraction_quality = "alta"
        elif confidence >= 0.7:
            extraction_quality = "media"
        elif confidence > 0:
            extraction_quality = "baixa"
        else:
            extraction_quality = "nao_avaliada"

        suggested_actions = []
        if not text_source:
            suggested_actions.append("Processar OCR para extrair texto pesquisavel do arquivo.")
        if text_source and extraction_quality in {"baixa", "nao_avaliada"}:
            suggested_actions.append("Revisar manualmente o texto extraido para melhorar a qualidade da base.")
        if document_row.get("case_id"):
            suggested_actions.append("Registrar comunicacao ao cliente com os principais pontos do documento.")
        if document_row.get("document_type") in {"contrato", "peticao", "procuracao"}:
            suggested_actions.append("Encaminhar o documento para assinatura digital ou validacao final.")
        if not suggested_actions:
            suggested_actions.append("Manter o documento vinculado ao processo e acompanhar a proxima acao relacionada.")

        risk_flags = []
        if not document_row.get("client_id"):
            risk_flags.append("Documento sem cliente vinculado.")
        if not document_row.get("case_id"):
            risk_flags.append("Documento sem processo vinculado.")
        if text_source and extraction_quality == "baixa":
            risk_flags.append("OCR com baixa confianca; recomenda-se revisao.")
        if not risk_flags:
            risk_flags.append("Nenhum risco operacional relevante identificado.")

        r.status = True
        r.message = "Insights do documento carregados com sucesso"
        r.data = {
            "document_id": str(document_row["id"]),
            "summary": summary,
            "keywords": keywords,
            "extraction_quality": extraction_quality,
            "ocr_status": ocr_row.get("status") if ocr_row else "nao_processado",
            "engine": ocr_row.get("engine") if ocr_row else "",
            "confidence_score": confidence,
            "client_name": document_row.get("client_name") or "",
            "case_number": document_row.get("case_number") or "",
            "risk_flags": risk_flags,
            "suggested_actions": suggested_actions,
        }
    except Exception as exc:
        r.make_error(0, "Erro ao carregar insights do documento", str(exc))
    finally:
        nx.stop()

    return r


def client_ai_insights(client_id: str, session_payload: dict) -> NXResult:
    r = NXResult()
    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        company_id = session_payload["company_id"]

        nx.xp_nx.execute(
            """
            SELECT id, name, status, email, phone, created_at
            FROM clients
            WHERE company_id = %s AND id = %s AND deleted_at IS NULL
            LIMIT 1
            """,
            (company_id, client_id),
        )
        client_row = nx.xp_nx.fetchone()
        if not client_row:
            r.make_error(404, "Cliente nao localizado")
            return r

        nx.xp_nx.execute(
            """
            SELECT
                COUNT(*) AS total_cases,
                COUNT(*) FILTER (WHERE status IN ('open', 'in_progress', 'active')) AS active_cases,
                COUNT(*) FILTER (WHERE status IN ('archived', 'closed', 'done')) AS closed_cases
            FROM cases
            WHERE company_id = %s AND client_id = %s AND deleted_at IS NULL
            """,
            (company_id, client_id),
        )
        cases_row = nx.xp_nx.fetchone()

        nx.xp_nx.execute(
            """
            SELECT
                COUNT(*) AS total_messages,
                MAX(COALESCE(sent_at, created_at)) AS last_contact_at
            FROM messages
            WHERE company_id = %s AND client_id = %s
            """,
            (company_id, client_id),
        )
        messages_row = nx.xp_nx.fetchone()

        nx.xp_nx.execute(
            """
            SELECT COUNT(*) AS total_documents
            FROM documents
            WHERE company_id = %s AND client_id = %s AND deleted_at IS NULL
            """,
            (company_id, client_id),
        )
        documents_row = nx.xp_nx.fetchone()

        nx.xp_nx.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE deleted_at IS NULL) AS total_items,
                COUNT(*) FILTER (
                    WHERE deleted_at IS NULL
                      AND COALESCE(due_at, start_at) IS NOT NULL
                      AND COALESCE(due_at, start_at) < NOW()
                      AND status NOT IN ('done', 'completed', 'cancelled')
                ) AS overdue_items,
                COUNT(*) FILTER (
                    WHERE deleted_at IS NULL
                      AND COALESCE(due_at, start_at) >= NOW()
                ) AS upcoming_items
            FROM (
                SELECT due_at, NULL::timestamp AS start_at, status, deleted_at
                FROM tasks
                WHERE company_id = %s AND client_id = %s
                UNION ALL
                SELECT NULL::timestamp AS due_at, start_at, status, deleted_at
                FROM appointments
                WHERE company_id = %s AND client_id = %s
            ) items
            """,
            (company_id, client_id, company_id, client_id),
        )
        agenda_row = nx.xp_nx.fetchone()

        total_cases = int(cases_row["total_cases"] or 0)
        active_cases = int(cases_row["active_cases"] or 0)
        total_messages = int(messages_row["total_messages"] or 0)
        total_documents = int(documents_row["total_documents"] or 0)
        overdue_items = int(agenda_row["overdue_items"] or 0)
        upcoming_items = int(agenda_row["upcoming_items"] or 0)

        relationship_score = 94
        if not total_messages:
            relationship_score -= 20
        elif total_messages < 3:
            relationship_score -= 8
        if overdue_items:
            relationship_score -= min(overdue_items * 10, 30)
        if not total_documents:
            relationship_score -= 10
        if not active_cases and total_cases:
            relationship_score -= 6
        relationship_score = max(25, min(99, relationship_score))

        if overdue_items >= 2:
            engagement_risk = "alto"
        elif overdue_items == 1 or not total_messages:
            engagement_risk = "medio"
        else:
            engagement_risk = "baixo"

        summary = (
            f"Cliente {client_row.get('name') or 'sem nome'} com {total_cases} processo(s), "
            f"{active_cases} ativo(s), {total_documents} documento(s) e {total_messages} comunicação(ões) registrada(s)."
        )

        suggested_actions = []
        if not total_messages:
            suggested_actions.append("Registrar um primeiro contato estruturado para abrir o histórico de relacionamento.")
        if overdue_items:
            suggested_actions.append("Priorizar os itens da agenda vencidos vinculados a este cliente.")
        if active_cases and upcoming_items == 0:
            suggested_actions.append("Criar novo item da agenda para acompanhamento ativo do cliente.")
        if total_documents < max(1, total_cases):
            suggested_actions.append("Revisar a pasta documental para complementar arquivos essenciais do cliente.")
        if not suggested_actions:
            suggested_actions.append("Manter o acompanhamento atual e revisar o relacionamento após a próxima movimentação.")

        risk_flags = []
        if not client_row.get("email") and not client_row.get("phone"):
            risk_flags.append("Cliente sem canal de contato principal cadastrado.")
        if overdue_items:
            risk_flags.append("Existem itens da agenda vencidos relacionados a este cliente.")
        if not total_documents:
            risk_flags.append("Cliente ainda não possui documentos vinculados.")
        if not risk_flags:
            risk_flags.append("Nenhum risco operacional relevante identificado para este cliente.")

        r.status = True
        r.message = "Insights do cliente carregados com sucesso"
        r.data = {
            "client_id": str(client_row["id"]),
            "summary": summary,
            "relationship_score": relationship_score,
            "engagement_risk": engagement_risk,
            "total_cases": total_cases,
            "active_cases": active_cases,
            "total_documents": total_documents,
            "total_messages": total_messages,
            "overdue_items": overdue_items,
            "upcoming_items": upcoming_items,
            "last_contact_at": messages_row.get("last_contact_at"),
            "risk_flags": risk_flags,
            "suggested_actions": suggested_actions,
        }
    except Exception as exc:
        r.make_error(0, "Erro ao carregar insights do cliente", str(exc))
    finally:
        nx.stop()

    return r


def dashboard_ai_insights(session_payload: dict) -> NXResult:
    r = NXResult()
    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        company_id = session_payload["company_id"]

        nx.xp_nx.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE deleted_at IS NULL AND status IN ('open', 'pending', 'in_progress')) AS open_tasks,
                COUNT(*) FILTER (
                    WHERE deleted_at IS NULL
                      AND due_at IS NOT NULL
                      AND due_at < NOW()
                      AND status NOT IN ('done', 'completed')
                ) AS overdue_tasks
            FROM tasks
            WHERE company_id = %s
            """,
            (company_id,),
        )
        tasks_row = nx.xp_nx.fetchone()

        nx.xp_nx.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE deleted_at IS NULL AND start_at >= NOW()) AS upcoming_appointments,
                MIN(start_at) FILTER (WHERE deleted_at IS NULL AND start_at >= NOW()) AS next_appointment_at
            FROM appointments
            WHERE company_id = %s
            """,
            (company_id,),
        )
        appointments_row = nx.xp_nx.fetchone()

        nx.xp_nx.execute(
            """
            SELECT COUNT(*) AS total_new_clients
            FROM clients
            WHERE company_id = %s
              AND deleted_at IS NULL
              AND created_at >= NOW() - INTERVAL '30 days'
            """,
            (company_id,),
        )
        clients_row = nx.xp_nx.fetchone()

        nx.xp_nx.execute(
            """
            SELECT COUNT(*) AS total_documents
            FROM documents
            WHERE company_id = %s AND deleted_at IS NULL
            """,
            (company_id,),
        )
        documents_row = nx.xp_nx.fetchone()

        nx.xp_nx.execute(
            """
            SELECT COALESCE(c.name, 'Cliente nao informado') AS client_name,
                   COUNT(*) AS total
            FROM tasks t
            LEFT JOIN clients c ON c.id = t.client_id
            WHERE t.company_id = %s
              AND t.deleted_at IS NULL
              AND t.due_at IS NOT NULL
              AND t.due_at < NOW()
              AND t.status NOT IN ('done', 'completed')
            GROUP BY COALESCE(c.name, 'Cliente nao informado')
            ORDER BY total DESC, client_name ASC
            LIMIT 1
            """,
            (company_id,),
        )
        critical_client_row = nx.xp_nx.fetchone()

        open_tasks = int(tasks_row["open_tasks"] or 0)
        overdue_tasks = int(tasks_row["overdue_tasks"] or 0)
        upcoming_appointments = int(appointments_row["upcoming_appointments"] or 0)
        total_new_clients = int(clients_row["total_new_clients"] or 0)
        total_documents = int(documents_row["total_documents"] or 0)

        operation_health = 92
        if overdue_tasks:
            operation_health -= min(overdue_tasks * 10, 30)
        if not upcoming_appointments:
            operation_health -= 12
        if open_tasks >= 8:
            operation_health -= 8
        if not total_documents:
            operation_health -= 5
        operation_health = max(30, min(99, operation_health))

        priority_alerts = []
        if overdue_tasks:
            priority_alerts.append(f"Existem {overdue_tasks} item(ns) vencido(s) na operação.")
        if not upcoming_appointments:
            priority_alerts.append("Nenhum compromisso futuro registrado na agenda.")
        if critical_client_row and int(critical_client_row["total"] or 0) > 0:
            priority_alerts.append(
                f"O cliente {critical_client_row['client_name']} concentra o maior volume de pendências vencidas."
            )
        if not priority_alerts:
            priority_alerts.append("A operação está sem alertas críticos imediatos.")

        recommendations = []
        if overdue_tasks:
            recommendations.append("Repriorizar a agenda da equipe para zerar os itens vencidos nas próximas 24 horas.")
        if upcoming_appointments < 3:
            recommendations.append("Adicionar compromissos de acompanhamento para os processos mais ativos da semana.")
        if total_new_clients and total_documents < total_new_clients:
            recommendations.append("Revisar onboarding documental dos clientes novos para evitar lacunas operacionais.")
        if not recommendations:
            recommendations.append("Manter o ritmo atual e revisar o painel novamente ao fim do dia.")

        executive_summary = (
            f"A operação atual possui {open_tasks} item(ns) em andamento, "
            f"{overdue_tasks} vencido(s), {upcoming_appointments} compromisso(s) futuro(s) "
            f"e {total_new_clients} novo(s) cliente(s) nos últimos 30 dias."
        )

        r.status = True
        r.message = "Insights executivos do dashboard carregados com sucesso"
        r.data = {
            "operation_health": operation_health,
            "executive_summary": executive_summary,
            "priority_alerts": priority_alerts,
            "recommendations": recommendations,
            "open_tasks": open_tasks,
            "overdue_tasks": overdue_tasks,
            "upcoming_appointments": upcoming_appointments,
            "new_clients_30d": total_new_clients,
            "documents_count": total_documents,
            "next_appointment_at": appointments_row.get("next_appointment_at"),
        }
    except Exception as exc:
        r.make_error(0, "Erro ao carregar insights executivos do dashboard", str(exc))
    finally:
        nx.stop()

    return r


def communication_ai_insights(message_id: str, session_payload: dict) -> NXResult:
    r = NXResult()
    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        company_id = session_payload["company_id"]

        nx.xp_nx.execute(
            """
            SELECT m.id, m.subject, m.body, m.channel, m.status, m.recipient, m.client_id, m.case_id,
                   m.sent_at, m.created_at,
                   c.name AS client_name,
                   cs.case_number
            FROM messages m
            LEFT JOIN clients c ON c.id = m.client_id
            LEFT JOIN cases cs ON cs.id = m.case_id
            WHERE m.company_id = %s AND m.id = %s
            LIMIT 1
            """,
            (company_id, message_id),
        )
        message_row = nx.xp_nx.fetchone()
        if not message_row:
            r.make_error(404, "Comunicacao nao localizada")
            return r

        client_id = message_row.get("client_id")
        case_id = message_row.get("case_id")

        next_action_due = None
        if client_id or case_id:
            nx.xp_nx.execute(
                """
                SELECT COALESCE(due_at, start_at) AS next_due
                FROM (
                    SELECT due_at, NULL::timestamp AS start_at, deleted_at, status
                    FROM tasks
                    WHERE company_id = %s
                      AND (%s = '' OR client_id = %s)
                      AND (%s = '' OR case_id = %s)
                    UNION ALL
                    SELECT NULL::timestamp AS due_at, start_at, deleted_at, status
                    FROM appointments
                    WHERE company_id = %s
                      AND (%s = '' OR client_id = %s)
                      AND (%s = '' OR case_id = %s)
                ) items
                WHERE deleted_at IS NULL
                  AND COALESCE(due_at, start_at) >= NOW()
                ORDER BY next_due ASC
                LIMIT 1
                """,
                (
                    company_id,
                    str(client_id or ""), str(client_id or ""),
                    str(case_id or ""), str(case_id or ""),
                    company_id,
                    str(client_id or ""), str(client_id or ""),
                    str(case_id or ""), str(case_id or ""),
                ),
            )
            next_row = nx.xp_nx.fetchone()
            next_action_due = next_row["next_due"] if next_row else None

        body_text = (message_row.get("body") or "").strip()
        body_size = len(body_text)
        if body_size > 1200:
            message_depth = "detalhada"
        elif body_size > 350:
            message_depth = "equilibrada"
        else:
            message_depth = "curta"

        follow_up_risk = "baixo"
        if str(message_row.get("status") or "").lower() == "failed":
            follow_up_risk = "alto"
        elif str(message_row.get("status") or "").lower() in {"draft", "queued"}:
            follow_up_risk = "medio"
        elif not next_action_due:
            follow_up_risk = "medio"

        summary = (
            f"Comunicação via {message_row.get('channel') or 'canal nao informado'} "
            f"com status {message_row.get('status') or 'sem status'} "
            f"para {message_row.get('client_name') or message_row.get('recipient') or 'destinatario nao identificado'}."
        )

        recommendations = []
        if str(message_row.get("status") or "").lower() == "failed":
            recommendations.append("Reenviar a comunicação ou trocar o canal de contato prioritariamente.")
        if str(message_row.get("status") or "").lower() == "draft":
            recommendations.append("Finalizar o rascunho e definir envio ou descarte para evitar fila parada.")
        if not next_action_due:
            recommendations.append("Criar item da agenda para garantir continuidade após esta comunicação.")
        if message_depth == "curta":
            recommendations.append("Complementar a mensagem com contexto ou anexos quando o tema exigir formalidade maior.")
        if not recommendations:
            recommendations.append("Manter o acompanhamento e registrar resposta ou próxima ação quando houver retorno.")

        suggested_follow_up = (
            "Retomar contato com atualização objetiva do processo e confirmar recebimento desta mensagem."
            if follow_up_risk != "baixo"
            else "Registrar resposta do cliente ou próxima movimentação assim que houver retorno."
        )

        r.status = True
        r.message = "Insights da comunicacao carregados com sucesso"
        r.data = {
            "message_id": str(message_row["id"]),
            "summary": summary,
            "follow_up_risk": follow_up_risk,
            "message_depth": message_depth,
            "next_action_due": next_action_due,
            "recommendations": recommendations,
            "suggested_follow_up": suggested_follow_up,
            "client_name": message_row.get("client_name") or "",
            "case_number": message_row.get("case_number") or "",
        }
    except Exception as exc:
        r.make_error(0, "Erro ao carregar insights da comunicacao", str(exc))
    finally:
        nx.stop()

    return r

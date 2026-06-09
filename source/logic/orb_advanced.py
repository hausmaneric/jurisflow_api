import json
import re

import requests

from source.core.config.config import appConfig
from source.core.system.database import NXDatabaseConnection
from source.core.system.utils import NXResult
from source.logic.orb_audit import register_audit_log


def _has_permission(session_payload: dict, permission_code: str) -> bool:
    return permission_code in set(session_payload.get("permissions") or [])


def _json(value) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, default=str)


def _jsonable(value):
    return json.loads(_json(value))


CNJ_STATE_COURTS = {
    "01": "tjac",
    "02": "tjal",
    "03": "tjam",
    "04": "tjap",
    "05": "tjba",
    "06": "tjce",
    "07": "tjdft",
    "08": "tjes",
    "09": "tjgo",
    "10": "tjma",
    "11": "tjmt",
    "12": "tjms",
    "13": "tjmg",
    "14": "tjpa",
    "15": "tjpb",
    "16": "tjpr",
    "17": "tjpe",
    "18": "tjpi",
    "19": "tjrj",
    "20": "tjrn",
    "21": "tjrs",
    "22": "tjro",
    "23": "tjrr",
    "24": "tjsc",
    "25": "tjse",
    "26": "tjsp",
    "27": "tjto",
}


def _digits(value: str | None) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _format_cnj_number(value: str | None) -> str:
    digits = _digits(value)
    if len(digits) != 20:
        return str(value or "")
    return f"{digits[:7]}-{digits[7:9]}.{digits[9:13]}.{digits[13]}.{digits[14:16]}.{digits[16:]}"


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def _court_slug(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _infer_datajud_court(case_row: dict, payload: dict) -> str:
    explicit = payload.get("datajud_court") or payload.get("court_code") or payload.get("court_system")
    if explicit:
        return _court_slug(explicit)

    court_text = _court_slug(case_row.get("court"))
    known = [
        "tjsp", "tjrj", "tjmg", "tjrs", "tjpr", "tjsc", "tjba", "tjgo", "tjpe", "tjce",
        "trf1", "trf2", "trf3", "trf4", "trf5", "trf6", "tst", "tse", "stm", "stj",
    ]
    for item in known:
        if item in court_text:
            return item

    number = _digits(case_row.get("case_number"))
    if len(number) == 20:
        justice_branch = number[13]
        court_code = number[14:16]
        if justice_branch == "8":
            return CNJ_STATE_COURTS.get(court_code, "")
        if justice_branch == "4":
            return f"trf{int(court_code)}" if court_code.isdigit() else ""
        if justice_branch == "5":
            return "trt" + court_code.lstrip("0")

    return ""


def _datajud_court_label(court: str) -> str:
    court = _court_slug(court)
    labels = {
        "stf": "Supremo Tribunal Federal",
        "stj": "Superior Tribunal de Justica",
        "tst": "Tribunal Superior do Trabalho",
        "tse": "Tribunal Superior Eleitoral",
        "stm": "Superior Tribunal Militar",
    }
    if court in labels:
        return labels[court]
    if court.startswith("tj"):
        return f"Tribunal de Justica - {court[2:].upper()}"
    if court.startswith("trf"):
        return f"Tribunal Regional Federal da {court[3:]}a Regiao"
    if court.startswith("trt"):
        return f"Tribunal Regional do Trabalho da {court[3:]}a Regiao"
    return court.upper() if court else ""


def _extract_source(hit: dict) -> dict:
    return hit.get("_source") or hit.get("source") or hit


def _extract_movements(source_data: dict) -> list[dict]:
    movements = source_data.get("movimentos") or source_data.get("movements") or []
    return movements if isinstance(movements, list) else []


def _movement_title(movement: dict) -> str:
    if movement.get("nome"):
        return str(movement["nome"])
    if isinstance(movement.get("movimentoNacional"), dict):
        return str(movement["movimentoNacional"].get("nome") or "Movimentacao importada")
    return str(movement.get("title") or movement.get("descricao") or "Movimentacao importada")


def _movement_date(movement: dict):
    value = movement.get("dataHora") or movement.get("data") or movement.get("movement_date")
    return str(value)[:10] if value else None


def _insert_sync_log(nx, session_payload: dict, case_id: str, source: str, payload: dict, raw_data: dict, status: str, error_message: str | None = None):
    nx.xp_nx.execute(
        """
        INSERT INTO case_sync_logs (
            company_id, case_id, lawyer_id, source, court_system, status, started_at, finished_at,
            documents_found, documents_downloaded, movements_imported, error_message, raw_data, created_by
        )
        VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW(), %s, %s, %s, %s, %s::jsonb, %s)
        RETURNING id, source, status, started_at, finished_at, documents_found, documents_downloaded, movements_imported, error_message
        """,
        (
            session_payload["company_id"],
            case_id,
            payload.get("lawyer_id"),
            source,
            payload.get("court_system") or payload.get("datajud_court") or payload.get("court_code"),
            status,
            _safe_int(payload.get("documents_found")),
            _safe_int(payload.get("documents_downloaded")),
            _safe_int(payload.get("movements_imported")),
            error_message or payload.get("error_message"),
            _json(raw_data),
            session_payload.get("user_id"),
        ),
    )
    return nx.xp_nx.fetchone()


def _call_datajud(case_row: dict, payload: dict) -> dict:
    if not appConfig.datajudApiKey:
        raise RuntimeError("JURISFLOW_DATAJUD_API_KEY nao configurada")

    court = _infer_datajud_court(case_row, payload)
    if not court:
        raise RuntimeError("Nao foi possivel identificar o tribunal DataJud do processo")

    process_number = _digits(payload.get("case_number") or case_row.get("case_number"))
    if len(process_number) < 20:
        raise RuntimeError("Numero do processo invalido para consulta DataJud")

    endpoint = f"{appConfig.datajudBaseUrl.rstrip('/')}/api_publica_{court}/_search"
    body = {
        "query": {
            "match": {
                "numeroProcesso": process_number
            }
        },
        "size": _safe_int(payload.get("size"), 10),
    }
    response = requests.post(
        endpoint,
        headers={"Authorization": f"APIKey {appConfig.datajudApiKey}", "Content-Type": "application/json"},
        json=body,
        timeout=30,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"DataJud retornou HTTP {response.status_code}: {response.text[:500]}")
    data = response.json()
    hits = data.get("hits", {}).get("hits", [])
    return {"court": court, "endpoint": endpoint, "request": body, "response": data, "hits": hits}


def _sync_datajud_case(nx, case_id: str, case_row: dict, session_payload: dict, payload: dict) -> dict:
    result = _call_datajud(case_row, payload)
    hits = result["hits"]
    source_data = _extract_source(hits[0]) if hits else {}
    movements = _extract_movements(source_data)
    imported = 0

    if source_data:
        court_name = (
            source_data.get("tribunal")
            or source_data.get("siglaTribunal")
            or result["court"].upper()
        )
        court_branch = ""
        if isinstance(source_data.get("orgaoJulgador"), dict):
            court_branch = source_data["orgaoJulgador"].get("nome") or ""
        phase = ""
        if isinstance(source_data.get("classe"), dict):
            phase = source_data["classe"].get("nome") or ""
        nx.xp_nx.execute(
            """
            UPDATE cases
            SET court = COALESCE(NULLIF(%s, ''), court),
                court_branch = COALESCE(NULLIF(%s, ''), court_branch),
                phase = COALESCE(NULLIF(%s, ''), phase),
                updated_at = NOW()
            WHERE id = %s AND company_id = %s
            """,
            (court_name, court_branch, phase, case_id, session_payload["company_id"]),
        )

    for movement in movements[:80]:
        title = _movement_title(movement)
        nx.xp_nx.execute(
            """
            INSERT INTO case_movements (company_id, case_id, source, movement_code, movement_date, title, description, raw_data)
            VALUES (%s, %s, 'datajud', %s, COALESCE(%s::date, CURRENT_DATE), %s, %s, %s::jsonb)
            """,
            (
                session_payload["company_id"],
                case_id,
                str(movement.get("codigo") or movement.get("code") or ""),
                _movement_date(movement),
                title,
                str(movement.get("descricao") or movement.get("complementosTabelados") or title),
                _json(movement),
            ),
        )
        imported += 1

    payload["court_system"] = result["court"]
    payload["movements_imported"] = imported
    log_row = _insert_sync_log(
        nx,
        session_payload,
        case_id,
        "datajud",
        payload,
        {"provider": "datajud", "court": result["court"], "hits": len(hits), "source": source_data},
        "success" if hits else "partial",
        None if hits else "DataJud nao retornou registros para o numero informado",
    )
    return {"log": dict(log_row), "hits": len(hits), "movements_imported": imported, "court": result["court"]}


def _sync_tribunal_case(nx, case_id: str, case_row: dict, session_payload: dict, payload: dict) -> dict:
    lawyer_id = payload.get("lawyer_id") or case_row.get("lawyer_id")
    if not lawyer_id:
        raise RuntimeError("Processo sem advogado responsavel para uso de certificado")

    nx.xp_nx.execute(
        """
        SELECT id, certificate_name, certificate_type, certificate_file_url, status, valid_until, consent_accepted
        FROM lawyer_certificates
        WHERE company_id = %s AND lawyer_id = %s AND deleted_at IS NULL
          AND status IN ('valid', 'active')
          AND consent_accepted = TRUE
          AND (valid_until IS NULL OR valid_until >= CURRENT_DATE)
        ORDER BY valid_until NULLS LAST, created_at DESC
        LIMIT 1
        """,
        (session_payload["company_id"], lawyer_id),
    )
    certificate = nx.xp_nx.fetchone()
    if not certificate:
        raise RuntimeError("Advogado sem certificado ativo, valido e autorizado")

    court_system = payload.get("court_system") or payload.get("court_code") or _infer_datajud_court(case_row, payload)
    nx.xp_nx.execute(
        """
        SELECT id, court_code, court_name, court_system, base_url, status, supports_certificate, settings
        FROM court_connectors
        WHERE company_id = %s AND deleted_at IS NULL
          AND supports_certificate = TRUE
          AND status IN ('active', 'available', 'configured', 'operational')
          AND (court_system ILIKE %s OR court_code ILIKE %s OR court_name ILIKE %s)
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (session_payload["company_id"], f"%{court_system}%", f"%{court_system}%", f"%{court_system}%"),
    )
    connector = nx.xp_nx.fetchone()
    if not connector or not connector.get("base_url"):
        raise RuntimeError("Conector do tribunal nao configurado para este processo")

    settings = connector.get("settings") or {}
    if isinstance(settings, str):
        settings = json.loads(settings or "{}")
    endpoint = str(settings.get("sync_endpoint") or connector["base_url"]).rstrip("/")
    body = {
        "case_number": _digits(case_row.get("case_number")),
        "case_id": str(case_id),
        "court_system": connector.get("court_system"),
        "certificate": {
            "id": str(certificate["id"]),
            "type": certificate.get("certificate_type"),
            "file_url": certificate.get("certificate_file_url"),
        },
    }
    headers = {"Content-Type": "application/json"}
    if settings.get("api_key"):
        headers["Authorization"] = f"Bearer {settings['api_key']}"
    response = requests.post(endpoint, json=body, headers=headers, timeout=_safe_int(settings.get("timeout"), 60))
    if response.status_code >= 400:
        raise RuntimeError(f"Conector do tribunal retornou HTTP {response.status_code}: {response.text[:500]}")
    data = response.json()

    documents = data.get("documents") or []
    movements = data.get("movements") or []
    for document in documents[:80]:
        nx.xp_nx.execute(
            """
            INSERT INTO case_documents_synced (company_id, case_id, title, source, file_url, file_type, external_id, status, raw_data)
            VALUES (%s, %s, %s, 'tribunal', %s, %s, %s, %s, %s::jsonb)
            """,
            (
                session_payload["company_id"],
                case_id,
                document.get("title") or document.get("name") or "Documento do tribunal",
                document.get("file_url") or document.get("url"),
                document.get("file_type") or document.get("type") or "pdf",
                document.get("external_id"),
                document.get("status") or "imported",
                _json(document),
            ),
        )
    for movement in movements[:80]:
        nx.xp_nx.execute(
            """
            INSERT INTO case_movements (company_id, case_id, source, movement_code, movement_date, title, description, raw_data)
            VALUES (%s, %s, 'tribunal', %s, COALESCE(%s::date, CURRENT_DATE), %s, %s, %s::jsonb)
            """,
            (
                session_payload["company_id"],
                case_id,
                movement.get("code"),
                _movement_date(movement),
                _movement_title(movement),
                movement.get("description") or movement.get("descricao"),
                _json(movement),
            ),
        )

    payload["documents_found"] = len(documents)
    payload["documents_downloaded"] = len(documents)
    payload["movements_imported"] = len(movements)
    payload["court_system"] = connector.get("court_system")
    log_row = _insert_sync_log(nx, session_payload, case_id, "tribunal", payload, {"connector_id": str(connector["id"]), "response": data}, "success")
    register_audit_log(session_payload["company_id"], session_payload.get("user_id"), "lawyer_certificates", str(certificate["id"]), "certificate_use", None, {"case_id": case_id, "connector_id": str(connector["id"])})
    return {"log": dict(log_row), "documents_imported": len(documents), "movements_imported": len(movements)}


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


def diagnose_case_sync(case_id: str, session_payload: dict, payload: dict | None = None) -> NXResult:
    r = NXResult()
    if not _has_permission(session_payload, "sync.read"):
        r.make_error(403, "Permissao insuficiente para diagnosticar consulta processual")
        return r

    payload = payload or {}
    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            """
            SELECT id, client_id, lawyer_id, case_number, title, court, court_branch, phase
            FROM cases
            WHERE id = %s AND company_id = %s AND deleted_at IS NULL
            """,
            (case_id, session_payload["company_id"]),
        )
        case_row = nx.xp_nx.fetchone()
        if not case_row:
            r.make_error(404, "Processo nao localizado")
            return r

        case_dict = dict(case_row)
        process_number = _digits(case_dict.get("case_number"))
        inferred_court = _infer_datajud_court(case_dict, payload)
        lawyer_id = payload.get("lawyer_id") or case_dict.get("lawyer_id")

        certificate = None
        expired_certificates = 0
        if lawyer_id:
            nx.xp_nx.execute(
                """
                SELECT id, certificate_name, certificate_type, issuer, valid_until, status, consent_accepted, last_validated_at
                FROM lawyer_certificates
                WHERE company_id = %s AND lawyer_id = %s AND deleted_at IS NULL
                  AND status IN ('valid', 'active')
                  AND consent_accepted = TRUE
                  AND (valid_until IS NULL OR valid_until >= CURRENT_DATE)
                ORDER BY valid_until NULLS LAST, created_at DESC
                LIMIT 1
                """,
                (session_payload["company_id"], lawyer_id),
            )
            certificate = nx.xp_nx.fetchone()

            nx.xp_nx.execute(
                """
                SELECT COUNT(*) AS total
                FROM lawyer_certificates
                WHERE company_id = %s AND lawyer_id = %s AND deleted_at IS NULL
                  AND valid_until IS NOT NULL AND valid_until < CURRENT_DATE
                """,
                (session_payload["company_id"], lawyer_id),
            )
            expired_certificates = int((nx.xp_nx.fetchone() or {}).get("total") or 0)

        connector = None
        if inferred_court:
            nx.xp_nx.execute(
                """
                SELECT id, court_code, court_name, court_system, base_url, status, supports_public_lookup, supports_certificate, settings
                FROM court_connectors
                WHERE company_id = %s AND deleted_at IS NULL
                  AND supports_certificate = TRUE
                  AND status IN ('active', 'available', 'configured', 'operational')
                  AND (court_system ILIKE %s OR court_code ILIKE %s OR court_name ILIKE %s)
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (session_payload["company_id"], f"%{inferred_court}%", f"%{inferred_court}%", f"%{inferred_court}%"),
            )
            connector = nx.xp_nx.fetchone()

        checks = [
            {
                "key": "datajud_api_key",
                "label": "Chave DataJud configurada",
                "ready": bool(appConfig.datajudApiKey),
                "message": "Configure JURISFLOW_DATAJUD_API_KEY no Railway" if not appConfig.datajudApiKey else "Consulta gratuita liberada",
            },
            {
                "key": "case_number",
                "label": "Numero CNJ valido",
                "ready": len(process_number) == 20,
                "message": _format_cnj_number(process_number) if len(process_number) == 20 else "Informe um numero CNJ com 20 digitos",
            },
            {
                "key": "datajud_court",
                "label": "Tribunal DataJud identificado",
                "ready": bool(inferred_court),
                "message": _datajud_court_label(inferred_court) if inferred_court else "Informe tribunal/codigo ou corrija o numero CNJ",
            },
            {
                "key": "responsible_lawyer",
                "label": "Advogado responsavel vinculado",
                "ready": bool(lawyer_id),
                "message": "Advogado responsavel encontrado" if lawyer_id else "Vincule um advogado ao processo",
            },
            {
                "key": "lawyer_certificate",
                "label": "Certificado valido autorizado",
                "ready": bool(certificate),
                "message": "Certificado pronto para uso" if certificate else "Cadastre, autorize e valide o certificado do advogado",
            },
            {
                "key": "court_connector",
                "label": "Conector do tribunal configurado",
                "ready": bool(connector and connector.get("base_url")),
                "message": "Conector certificado encontrado" if connector and connector.get("base_url") else "Configure o conector do tribunal correto",
            },
        ]

        r.status = True
        r.message = "Diagnostico da consulta processual carregado"
        r.data = {
            "case": {
                "id": str(case_dict["id"]),
                "case_number": case_dict.get("case_number"),
                "normalized_case_number": _format_cnj_number(process_number),
                "court": case_dict.get("court"),
                "lawyer_id": str(lawyer_id) if lawyer_id else None,
            },
            "datajud": {
                "ready": all(item["ready"] for item in checks[:3]),
                "court": inferred_court,
                "court_label": _datajud_court_label(inferred_court),
                "base_url": appConfig.datajudBaseUrl,
            },
            "tribunal": {
                "ready": all(item["ready"] for item in checks),
                "certificate": dict(certificate) if certificate else None,
                "expired_certificates": expired_certificates,
                "connector": dict(connector) if connector else None,
            },
            "checks": checks,
        }
    except Exception as exc:
        r.make_error(0, "Erro ao diagnosticar consulta processual", str(exc))
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
            "SELECT id, client_id, lawyer_id, case_number, title, court, court_branch, phase FROM cases WHERE id = %s AND company_id = %s AND deleted_at IS NULL",
            (case_id, session_payload["company_id"]),
        )
        case_row = nx.xp_nx.fetchone()
        if not case_row:
            r.make_error(404, "Processo nao localizado")
            return r

        if source == "datajud":
            sync_data = {"datajud": _sync_datajud_case(nx, case_id, case_row, session_payload, payload)}
            message = "Consulta DataJud concluida"
        elif source == "tribunal":
            sync_data = {"tribunal": _sync_tribunal_case(nx, case_id, case_row, session_payload, payload)}
            message = "Consulta ao tribunal concluida"
        elif source == "full":
            sync_data = {"datajud": _sync_datajud_case(nx, case_id, case_row, session_payload, payload)}
            try:
                sync_data["tribunal"] = _sync_tribunal_case(nx, case_id, case_row, session_payload, payload)
                message = "Sincronizacao completa concluida"
            except Exception as tribunal_exc:
                payload["error_message"] = str(tribunal_exc)
                payload["status"] = "partial"
                log_row = _insert_sync_log(
                    nx,
                    session_payload,
                    case_id,
                    "tribunal",
                    payload,
                    {"provider": "tribunal", "stage": "full_after_datajud"},
                    "partial",
                    str(tribunal_exc),
                )
                sync_data["tribunal"] = {"log": dict(log_row), "error": str(tribunal_exc)}
                message = "DataJud concluido; tribunal pendente de configuracao/certificado"
        else:
            r.make_error(0, "Origem de sincronizacao invalida")
            return r

        nx.conn_nx.commit()
        register_audit_log(session_payload["company_id"], session_payload.get("user_id"), "cases", case_id, f"sync_{source}", None, _jsonable(sync_data))
        r.status = True
        r.message = message
        r.data = {"case": dict(case_row), "sync": sync_data}
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
        segments = [dict(row) for row in nx.xp_nx.fetchall()]
        generated = _build_transcription_summary(segments)
        summary = payload.get("summary") or generated["summary"]
        key_points = payload.get("key_points") or generated["key_points"]
        next_steps = payload.get("next_steps") or generated["next_steps"]
        risks = payload.get("risks") or generated["risks"]
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

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        if not tasks:
            nx.xp_nx.execute(
                """
                SELECT text
                FROM transcription_segments
                WHERE transcription_id = %s AND company_id = %s AND deleted_at IS NULL
                ORDER BY start_seconds NULLS LAST, created_at ASC
                """,
                (transcription_id, session_payload["company_id"]),
            )
            segments = [dict(row) for row in nx.xp_nx.fetchall()]
            generated = _build_transcription_summary(segments)
            tasks = [
                {
                    "title": _task_title_from_text(step),
                    "description": step,
                    "priority": "media",
                    "status": "pending",
                }
                for step in generated["next_steps"][:6]
            ]

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


def _segment_text(text: str) -> list[dict]:
    chunks = [line.strip() for line in re.split(r"\n{2,}|\r\n{2,}", text or "") if line.strip()]
    if not chunks and text:
        chunks = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    return [
        {
            "speaker_label": "Transcricao",
            "start_seconds": index * 30,
            "end_seconds": (index + 1) * 30,
            "text": chunk,
            "confidence_score": 1,
        }
        for index, chunk in enumerate(chunks)
    ]


def _normalize_segments(segments: list[dict], provider: str) -> list[dict]:
    normalized = []
    for index, segment in enumerate(segments or []):
        text = str(segment.get("text") or segment.get("transcript") or "").strip()
        if not text:
            continue
        start = segment.get("start_seconds", segment.get("start", index * 30))
        end = segment.get("end_seconds", segment.get("end"))
        normalized.append(
            {
                "speaker_label": segment.get("speaker_label") or segment.get("speaker") or f"Fala {index + 1}",
                "start_seconds": _safe_int(start),
                "end_seconds": _safe_int(end, _safe_int(start) + 30) if end is not None else _safe_int(start) + 30,
                "text": text,
                "confidence_score": segment.get("confidence_score") or segment.get("confidence") or (1 if provider == "manual" else None),
                "reviewed": bool(segment.get("reviewed")) if provider != "manual" else True,
            }
        )
    return normalized


def _sentences_from_text(text: str) -> list[str]:
    sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+", text or "") if item.strip()]
    if not sentences and text:
        sentences = [text.strip()]
    return sentences


def _pick_sentences(sentences: list[str], keywords: list[str], limit: int) -> list[str]:
    selected = []
    for sentence in sentences:
        sentence_lower = sentence.lower()
        if any(keyword in sentence_lower for keyword in keywords):
            selected.append(sentence)
        if len(selected) >= limit:
            break
    return selected


def _build_transcription_summary(segments: list[dict]) -> dict:
    full_text = " ".join(str(segment.get("text") or "").strip() for segment in segments if segment.get("text")).strip()
    sentences = _sentences_from_text(full_text)
    summary_sentences = sentences[:4]
    summary = " ".join(summary_sentences)[:1600] if summary_sentences else "Transcricao sem conteudo suficiente para resumo."

    key_points = _pick_sentences(
        sentences,
        ["ficou definido", "foi definido", "acordado", "combinado", "importante", "cliente", "processo", "audiencia", "prazo", "documento"],
        8,
    )
    next_steps = _pick_sentences(
        sentences,
        ["providenciar", "enviar", "protocolar", "anexar", "preparar", "agendar", "retornar", "cobrar", "verificar", "acompanhar"],
        8,
    )
    risks = _pick_sentences(
        sentences,
        ["risco", "urgente", "prazo", "vencimento", "atraso", "pendente", "indefer", "multa", "bloqueio", "audiencia"],
        6,
    )

    if not key_points:
        key_points = sentences[:5]
    if not next_steps:
        next_steps = ["Revisar a transcricao e confirmar os encaminhamentos com o responsavel."]
    if not risks:
        risks = ["Nenhum risco objetivo identificado automaticamente; recomenda-se revisao juridica humana."]

    return {
        "summary": summary,
        "key_points": key_points,
        "next_steps": next_steps,
        "risks": risks,
    }


def _task_title_from_text(text: str) -> str:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    clean = re.sub(r"^(providenciar|enviar|protocolar|anexar|preparar|agendar|retornar|cobrar|verificar|acompanhar)\s+", lambda m: m.group(1).capitalize() + " ", clean, flags=re.I)
    return clean[:120] if clean else "Revisar encaminhamento da transcricao"


def _call_whisper_worker(transcription: dict, file_row: dict, payload: dict) -> list[dict]:
    if not appConfig.whisperWorkerUrl:
        raise RuntimeError("JURISFLOW_WHISPER_WORKER_URL nao configurada")

    headers = {"Content-Type": "application/json"}
    if appConfig.whisperWorkerToken:
        headers["Authorization"] = f"Bearer {appConfig.whisperWorkerToken}"

    response = requests.post(
        appConfig.whisperWorkerUrl.rstrip("/") + "/transcribe",
        headers=headers,
        json={
            "transcription_id": str(transcription["id"]),
            "file_url": file_row["file_url"],
            "language": payload.get("language") or transcription.get("language") or "pt-BR",
            "vocabulary": payload.get("vocabulary") or [],
            "metadata": {
                "client_id": str(transcription.get("client_id") or ""),
                "case_id": str(transcription.get("case_id") or ""),
                "type": transcription.get("transcription_type"),
            },
        },
        timeout=_safe_int(payload.get("timeout"), 300),
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Worker Whisper retornou HTTP {response.status_code}: {response.text[:500]}")
    data = response.json()
    segments = data.get("segments") or []
    if segments:
        return _normalize_segments(segments, "whisper_worker")
    if data.get("text"):
        return _normalize_segments(_segment_text(data["text"]), "whisper_worker")
    raise RuntimeError("Worker Whisper nao retornou segmentos nem texto")


def process_transcription(transcription_id: str, session_payload: dict, payload: dict) -> NXResult:
    r = NXResult()
    if not _has_permission(session_payload, "notes.write"):
        r.make_error(403, "Permissao insuficiente para processar transcricao")
        return r

    provider = (payload.get("provider") or appConfig.transcriptionProvider or "manual").lower()
    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            """
            SELECT id, company_id, client_id, case_id, appointment_id, title, language, transcription_type, status
            FROM transcriptions
            WHERE id = %s AND company_id = %s AND deleted_at IS NULL
            """,
            (transcription_id, session_payload["company_id"]),
        )
        transcription = nx.xp_nx.fetchone()
        if not transcription:
            r.make_error(404, "Transcricao nao localizada")
            return r

        nx.xp_nx.execute(
            """
            SELECT id, file_url, file_type, duration_seconds
            FROM transcription_files
            WHERE transcription_id = %s AND company_id = %s AND deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (transcription_id, session_payload["company_id"]),
        )
        file_row = nx.xp_nx.fetchone()

        if provider == "manual":
            text = payload.get("text") or payload.get("transcript") or payload.get("reviewed_text")
            if not text:
                r.make_error(0, "Para provider manual, informe text/transcript com o conteudo transcrito")
                return r
            segments = _normalize_segments(_segment_text(text), provider)
        elif provider == "whisper_worker":
            if not file_row:
                r.make_error(0, "Envie um arquivo antes de processar com whisper_worker")
                return r
            segments = _call_whisper_worker(dict(transcription), dict(file_row), payload)
        else:
            r.make_error(0, f"Provider de transcricao nao suportado: {provider}")
            return r

        nx.xp_nx.execute(
            "UPDATE transcription_segments SET deleted_at = NOW() WHERE transcription_id = %s AND company_id = %s AND deleted_at IS NULL",
            (transcription_id, session_payload["company_id"]),
        )
        for segment in segments:
            nx.xp_nx.execute(
                """
                INSERT INTO transcription_segments (
                    company_id, transcription_id, speaker_label, start_seconds, end_seconds, text, confidence_score, reviewed
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    session_payload["company_id"],
                    transcription_id,
                    segment["speaker_label"],
                    segment["start_seconds"],
                    segment["end_seconds"],
                    segment["text"],
                    segment["confidence_score"],
                    segment["reviewed"],
                ),
            )
        confidence_values = [
            float(segment["confidence_score"])
            for segment in segments
            if segment.get("confidence_score") is not None
        ]
        quality_score = int(round((sum(confidence_values) / len(confidence_values)) * 100)) if confidence_values else None
        nx.xp_nx.execute(
            """
            UPDATE transcriptions
            SET status = %s, quality_score = %s, updated_at = NOW()
            WHERE id = %s AND company_id = %s
            RETURNING id, title, status, quality_score, updated_at
            """,
            ("reviewed" if provider == "manual" else "transcribed", quality_score, transcription_id, session_payload["company_id"]),
        )
        updated = nx.xp_nx.fetchone()
        nx.conn_nx.commit()
        register_audit_log(session_payload["company_id"], session_payload.get("user_id"), "transcriptions", transcription_id, "process", None, {"provider": provider, "segments": len(segments)})
        r.status = True
        r.message = "Transcricao processada com sucesso"
        r.data = {"transcription": dict(updated), "segments": len(segments), "provider": provider}
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao processar transcricao", str(exc))
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

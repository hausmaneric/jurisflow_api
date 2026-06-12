import json
import hashlib
import re
import secrets

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


def _hash_agent_token(token: str) -> str:
    return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()


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

DATAJUD_COURTS = {
    "stj", "stm", "tse", "tst", "tre",
    "trf1", "trf2", "trf3", "trf4", "trf5", "trf6",
    "tjac", "tjal", "tjam", "tjap", "tjba", "tjce", "tjdft", "tjes", "tjgo", "tjma",
    "tjmg", "tjmmg", "tjmrs", "tjms", "tjmsp", "tjmt", "tjpa", "tjpb", "tjpe",
    "tjpi", "tjpr", "tjrj", "tjrn", "tjro", "tjrr", "tjrs", "tjsc", "tjse", "tjsp", "tjto",
    *{f"trt{item}" for item in range(1, 25)},
}

DATAJUD_COURT_ALIASES = {
    **{f"api_publica_{court}": court for court in DATAJUD_COURTS},
    "tjdf": "tjdft",
    "df": "tjdft",
    "justicaeleitoral": "tse",
    "eleitoral": "tse",
    "justicadotrabalho": "tst",
    "trabalho": "tst",
    "justicafederal": "trf1",
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
    value = re.sub(r"[^a-z0-9]", "", str(value or "").lower())
    return DATAJUD_COURT_ALIASES.get(value, value)


def _datajud_api_key() -> str:
    return str(appConfig.datajudApiKey or "").strip()


def _datajud_endpoint(court: str) -> str:
    court = _court_slug(court)
    if court not in DATAJUD_COURTS:
        raise RuntimeError(f"Tribunal DataJud invalido ou nao suportado: {court}")
    return f"{appConfig.datajudBaseUrl.rstrip('/')}/api_publica_{court}/_search"


def _datajud_request_body(payload: dict, process_number: str | None = None) -> dict:
    body = payload.get("query_dsl") or payload.get("dsl") or payload.get("body")
    if isinstance(body, str):
        body = json.loads(body)
    if not isinstance(body, dict):
        number = _digits(payload.get("numeroProcesso") or payload.get("case_number") or process_number)
        if len(number) != 20:
            raise RuntimeError("Informe um numeroProcesso/CNJ com 20 digitos ou um query_dsl valido")
        body = {"query": {"match": {"numeroProcesso": number}}}

    size = _safe_int(payload.get("size") or body.get("size"), 10)
    body["size"] = max(1, min(size, 10000))
    if payload.get("sort") is not None:
        body["sort"] = payload["sort"]
    if payload.get("search_after") is not None:
        body["search_after"] = payload["search_after"]
    if payload.get("search_after") is not None and not body.get("sort"):
        body["sort"] = [{"@timestamp": {"order": "asc"}}]
    return body


def _datajud_search(court: str, body: dict) -> dict:
    api_key = _datajud_api_key()
    if not api_key:
        raise RuntimeError("JURISFLOW_DATAJUD_API_KEY nao configurada")

    endpoint = _datajud_endpoint(court)
    response = requests.post(
        endpoint,
        headers={"Authorization": f"APIKey {api_key}", "Content-Type": "application/json"},
        json=body,
        timeout=30,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"DataJud retornou HTTP {response.status_code}: {response.text[:500]}")
    data = response.json()
    hits = data.get("hits", {}).get("hits", [])
    last_sort = hits[-1].get("sort") if hits else None
    total = data.get("hits", {}).get("total", 0)
    if isinstance(total, dict):
        total = total.get("value", 0)
    return {
        "court": _court_slug(court),
        "endpoint": endpoint,
        "request": body,
        "response": data,
        "hits": hits,
        "total": total,
        "next_search_after": last_sort,
    }


def _infer_datajud_court(case_row: dict, payload: dict) -> str:
    explicit = payload.get("datajud_court") or payload.get("court_code") or payload.get("court_system")
    if explicit:
        return _court_slug(explicit)

    court_text = _court_slug(case_row.get("court"))
    known = [
        "tjsp", "tjrj", "tjmg", "tjrs", "tjpr", "tjsc", "tjba", "tjgo", "tjpe", "tjce",
        "trf1", "trf2", "trf3", "trf4", "trf5", "trf6", "tst", "tse", "stm", "stj", "tre",
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
        if justice_branch == "6":
            return "tre"

    return ""


def _datajud_court_label(court: str) -> str:
    court = _court_slug(court)
    labels = {
        "stf": "Supremo Tribunal Federal",
        "stj": "Superior Tribunal de Justica",
        "tst": "Tribunal Superior do Trabalho",
        "tse": "Tribunal Superior Eleitoral",
        "stm": "Superior Tribunal Militar",
        "tre": "Tribunais Regionais Eleitorais",
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


def _court_system_family(court: str) -> str:
    court = _court_slug(court)
    if court.startswith("trt") or court == "tst":
        return "pje_trabalhista"
    if court.startswith("trf"):
        return "pje_federal"
    if court in {"tse", "tre"}:
        return "pje_eleitoral"
    if court in {"stj", "stm"}:
        return court
    if court.startswith("tjm"):
        return "pje_militar"
    return "tribunal_local_bridge"


def _default_connector_payload(court: str, sync_endpoint: str | None = None) -> dict:
    court = _court_slug(court)
    bridge_url = str(sync_endpoint or appConfig.localCourtBridgeUrl).rstrip("/")
    return {
        "court_code": court,
        "court_name": _datajud_court_label(court),
        "court_system": court,
        "base_url": bridge_url,
        "status": "configured",
        "supports_public_lookup": True,
        "supports_certificate": True,
        "settings": {
            "datajud_alias": f"api_publica_{court}",
            "system_family": _court_system_family(court),
            "sync_endpoint": bridge_url,
            "local_sync_endpoint": bridge_url,
            "server_sync_endpoint": "",
            "requires_local_agent": True,
            "certificate_modes": ["token_a3_local", "cloud_provider", "file_a1"],
            "expected_response": {"documents": [], "movements": []},
            "notes": (
                "Conector padrao hibrido: A1 por arquivo pode usar agente local ou endpoint remoto configurado; "
                "A3/token fisico sempre usa agente local. O Railway nao acessa token, PIN ou chave privada."
            ),
        },
    }


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


def _replace_tribunal_imports(nx, company_id: str, case_id: str, documents: list[dict], movements: list[dict]) -> tuple[int, int]:
    nx.xp_nx.execute(
        """
        UPDATE case_documents_synced
        SET deleted_at = NOW(), updated_at = NOW()
        WHERE company_id = %s AND case_id = %s AND source = 'tribunal' AND deleted_at IS NULL
        """,
        (company_id, case_id),
    )
    nx.xp_nx.execute(
        """
        UPDATE case_movements
        SET deleted_at = NOW(), updated_at = NOW()
        WHERE company_id = %s AND case_id = %s AND source = 'tribunal' AND deleted_at IS NULL
        """,
        (company_id, case_id),
    )

    imported_documents = 0
    imported_movements = 0
    for document in documents[:80]:
        nx.xp_nx.execute(
            """
            INSERT INTO case_documents_synced (company_id, case_id, title, source, file_url, file_type, external_id, status, raw_data)
            VALUES (%s, %s, %s, 'tribunal', %s, %s, %s, %s, %s::jsonb)
            """,
            (
                company_id,
                case_id,
                document.get("title") or document.get("name") or "Documento do tribunal",
                document.get("file_url") or document.get("url"),
                document.get("file_type") or document.get("type") or "pdf",
                document.get("external_id"),
                document.get("status") or "imported",
                _json(document),
            ),
        )
        imported_documents += 1
    for movement in movements[:80]:
        nx.xp_nx.execute(
            """
            INSERT INTO case_movements (company_id, case_id, source, movement_code, movement_date, title, description, raw_data)
            VALUES (%s, %s, 'tribunal', %s, COALESCE(%s::date, CURRENT_DATE), %s, %s, %s::jsonb)
            """,
            (
                company_id,
                case_id,
                movement.get("code"),
                _movement_date(movement),
                _movement_title(movement),
                movement.get("description") or movement.get("descricao"),
                _json(movement),
            ),
        )
        imported_movements += 1

    return imported_documents, imported_movements


def _call_datajud(case_row: dict, payload: dict) -> dict:
    court = _infer_datajud_court(case_row, payload)
    if not court:
        raise RuntimeError("Nao foi possivel identificar o tribunal DataJud do processo")

    process_number = _digits(payload.get("case_number") or case_row.get("case_number"))
    if len(process_number) != 20:
        raise RuntimeError("Numero do processo invalido para consulta DataJud")

    return _datajud_search(court, _datajud_request_body(payload, process_number))


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

    if source_data:
        nx.xp_nx.execute(
            """
            UPDATE case_movements
            SET deleted_at = NOW(), updated_at = NOW()
            WHERE company_id = %s AND case_id = %s AND source = 'datajud' AND deleted_at IS NULL
            """,
            (session_payload["company_id"], case_id),
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
        SELECT id, lawyer_id, certificate_name, certificate_type, certificate_access_mode, certificate_file_url,
               certificate_provider, device_identifier, local_agent_id, cloud_certificate_ref,
               metadata, status, valid_until, consent_accepted
        FROM lawyer_certificates
        WHERE company_id = %s AND deleted_at IS NULL
          AND (
            lawyer_id = %s
            OR lawyer_id IN (
                SELECT id FROM lawyers WHERE company_id = %s AND user_id = %s AND deleted_at IS NULL
            )
          )
          AND status IN ('valid', 'active')
          AND consent_accepted = TRUE
          AND (valid_until IS NULL OR valid_until >= CURRENT_DATE)
        ORDER BY valid_until NULLS LAST, created_at DESC
        LIMIT 1
        """,
        (session_payload["company_id"], lawyer_id, session_payload["company_id"], lawyer_id),
    )
    certificate = nx.xp_nx.fetchone()
    if not certificate:
        raise RuntimeError("Advogado sem certificado ativo, valido e autorizado")
    payload["lawyer_id"] = str(certificate.get("lawyer_id") or lawyer_id)
    certificate_access_mode = certificate.get("certificate_access_mode") or "file_a1"
    if certificate_access_mode == "file_a1" and not certificate.get("certificate_file_url"):
        raise RuntimeError("Certificado A1 sem arquivo seguro configurado")

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
    use_local_agent = bool(
        payload.get("use_local_agent")
        or settings.get("requires_local_agent")
        or (certificate_access_mode == "token_a3_local" and not settings.get("allow_server_side_a3"))
    )
    if certificate_access_mode == "file_a1" and settings.get("server_sync_endpoint") and not payload.get("use_local_agent"):
        use_local_agent = False

    endpoint = str(
        (settings.get("local_sync_endpoint") if use_local_agent else settings.get("server_sync_endpoint"))
        or settings.get("sync_endpoint")
        or connector["base_url"]
    ).rstrip("/")
    body = {
        "case_number": _digits(case_row.get("case_number")),
        "case_id": str(case_id),
        "court_system": connector.get("court_system"),
        "certificate": {
            "id": str(certificate["id"]),
            "type": certificate.get("certificate_type"),
            "access_mode": certificate_access_mode,
            "provider": certificate.get("certificate_provider"),
            "file_url": certificate.get("certificate_file_url"),
            "device_identifier": certificate.get("device_identifier"),
            "local_agent_id": certificate.get("local_agent_id"),
            "cloud_certificate_ref": certificate.get("cloud_certificate_ref"),
            "metadata": certificate.get("metadata") or {},
        },
    }
    headers = {"Content-Type": "application/json"}
    if settings.get("api_key"):
        headers["Authorization"] = f"Bearer {settings['api_key']}"
    if use_local_agent:
        assigned_agent_key = payload.get("local_agent_id") or payload.get("agent_key") or certificate.get("local_agent_id") or certificate.get("device_identifier")
        if not assigned_agent_key:
            raise RuntimeError(f"Certificado {certificate_access_mode} sem agente local configurado")
        nx.xp_nx.execute(
            """
            INSERT INTO certificate_agent_jobs (
                company_id, case_id, lawyer_id, certificate_id, connector_id, assigned_agent_key,
                job_type, status, request_payload, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, 'tribunal_sync', 'pending', %s::jsonb, %s)
            RETURNING id, status, assigned_agent_key, created_at
            """,
            (
                session_payload["company_id"],
                case_id,
                certificate.get("lawyer_id"),
                certificate["id"],
                connector["id"],
                assigned_agent_key,
                _json({"endpoint": endpoint, "headers": headers, "body": body, "connector_settings": settings}),
                session_payload.get("user_id"),
            ),
        )
        job = nx.xp_nx.fetchone()
        payload["court_system"] = connector.get("court_system")
        payload["error_message"] = f"Consulta aguardando agente local para certificado {certificate_access_mode}"
        log_row = _insert_sync_log(
            nx,
            session_payload,
            case_id,
            "tribunal",
            payload,
            {"connector_id": str(connector["id"]), "agent_job_id": str(job["id"]), "access_mode": certificate_access_mode},
            "pending",
            payload["error_message"],
        )
        return {"log": dict(log_row), "agent_job": dict(job), "status": "pending_agent"}

    response = requests.post(endpoint, json=body, headers=headers, timeout=_safe_int(settings.get("timeout"), 60))
    if response.status_code >= 400:
        raise RuntimeError(f"Conector do tribunal retornou HTTP {response.status_code}: {response.text[:500]}")
    data = response.json()

    documents = data.get("documents") or []
    movements = data.get("movements") or []
    imported_documents, imported_movements = _replace_tribunal_imports(nx, session_payload["company_id"], case_id, documents, movements)

    payload["documents_found"] = len(documents)
    payload["documents_downloaded"] = imported_documents
    payload["movements_imported"] = imported_movements
    payload["court_system"] = connector.get("court_system")
    log_row = _insert_sync_log(nx, session_payload, case_id, "tribunal", payload, {"connector_id": str(connector["id"]), "response": data}, "success")
    register_audit_log(session_payload["company_id"], session_payload.get("user_id"), "lawyer_certificates", str(certificate["id"]), "certificate_use", None, {"case_id": case_id, "connector_id": str(connector["id"])})
    return {"log": dict(log_row), "documents_imported": imported_documents, "movements_imported": imported_movements}


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
                    WHEN COALESCE(certificate_access_mode, 'file_a1') = 'file_a1'
                         AND COALESCE(certificate_file_url, '') = '' THEN 'invalid_config'
                    WHEN COALESCE(certificate_access_mode, 'file_a1') = 'token_a3_local'
                         AND COALESCE(local_agent_id, '') = ''
                         AND COALESCE(device_identifier, '') = '' THEN 'invalid_config'
                    WHEN COALESCE(certificate_access_mode, 'file_a1') = 'cloud_provider'
                         AND COALESCE(cloud_certificate_ref, '') = ''
                         AND COALESCE(certificate_provider, '') = '' THEN 'invalid_config'
                    ELSE 'valid'
                END,
                last_validated_at = NOW(),
                updated_at = NOW()
            WHERE company_id = %s AND lawyer_id = %s AND deleted_at IS NULL{certificate_filter}
            RETURNING id, lawyer_id, certificate_name, certificate_type, certificate_access_mode,
                      certificate_provider, device_identifier, local_agent_id, cloud_certificate_ref,
                      issuer, valid_from, valid_until, status, last_validated_at
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
                SELECT id, lawyer_id, certificate_name, certificate_type, certificate_access_mode, certificate_provider,
                       device_identifier, local_agent_id, cloud_certificate_ref, issuer, valid_until,
                       status, consent_accepted, last_validated_at
                FROM lawyer_certificates
                WHERE company_id = %s AND deleted_at IS NULL
                  AND (
                    lawyer_id = %s
                    OR lawyer_id IN (
                        SELECT id FROM lawyers WHERE company_id = %s AND user_id = %s AND deleted_at IS NULL
                    )
                  )
                  AND status IN ('valid', 'active')
                  AND consent_accepted = TRUE
                  AND (valid_until IS NULL OR valid_until >= CURRENT_DATE)
                ORDER BY valid_until NULLS LAST, created_at DESC
                LIMIT 1
                """,
                (session_payload["company_id"], lawyer_id, session_payload["company_id"], lawyer_id),
            )
            certificate = nx.xp_nx.fetchone()

            nx.xp_nx.execute(
                """
                SELECT COUNT(*) AS total
                FROM lawyer_certificates
                WHERE company_id = %s AND deleted_at IS NULL
                  AND (
                    lawyer_id = %s
                    OR lawyer_id IN (
                        SELECT id FROM lawyers WHERE company_id = %s AND user_id = %s AND deleted_at IS NULL
                    )
                  )
                  AND valid_until IS NOT NULL AND valid_until < CURRENT_DATE
                """,
                (session_payload["company_id"], lawyer_id, session_payload["company_id"], lawyer_id),
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
                "message": (
                    f"Certificado pronto para uso via {certificate.get('certificate_access_mode') or 'file_a1'}"
                    if certificate else "Cadastre, autorize e valide o certificado do advogado"
                ),
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


def list_datajud_courts(session_payload: dict) -> NXResult:
    r = NXResult()
    if not _has_permission(session_payload, "sync.read"):
        r.make_error(403, "Permissao insuficiente para listar tribunais DataJud")
        return r

    courts = []
    for court in sorted(DATAJUD_COURTS):
        courts.append({
            "court": court,
            "alias": f"api_publica_{court}",
            "label": _datajud_court_label(court),
            "endpoint": _datajud_endpoint(court),
        })
    r.status = True
    r.message = "Tribunais DataJud carregados"
    r.data = {
        "base_url": appConfig.datajudBaseUrl,
        "auth_header": "Authorization: APIKey <chave publica CNJ>",
        "courts": courts,
    }
    return r


def search_datajud_records(session_payload: dict, payload: dict) -> NXResult:
    r = NXResult()
    if not _has_permission(session_payload, "sync.read"):
        r.make_error(403, "Permissao insuficiente para consultar DataJud")
        return r

    try:
        court = payload.get("court") or payload.get("tribunal") or payload.get("datajud_court") or payload.get("court_code")
        if not court:
            case_like = {"case_number": payload.get("case_number") or payload.get("numeroProcesso"), "court": payload.get("court_name")}
            court = _infer_datajud_court(case_like, payload)
        if not court:
            raise RuntimeError("Informe o tribunal DataJud ou um numero CNJ que permita identificar o tribunal")

        body = _datajud_request_body(payload, payload.get("case_number") or payload.get("numeroProcesso"))
        result = _datajud_search(court, body)
        normalized_hits = []
        for hit in result["hits"]:
            source = _extract_source(hit)
            normalized_hits.append({
                "id": hit.get("_id"),
                "index": hit.get("_index"),
                "score": hit.get("_score"),
                "sort": hit.get("sort"),
                "numeroProcesso": source.get("numeroProcesso"),
                "classe": source.get("classe"),
                "tribunal": source.get("tribunal") or source.get("siglaTribunal") or result["court"].upper(),
                "orgaoJulgador": source.get("orgaoJulgador"),
                "grau": source.get("grau"),
                "dataAjuizamento": source.get("dataAjuizamento"),
                "movimentos": _extract_movements(source),
                "raw": source,
            })
        r.status = True
        r.message = "Consulta DataJud concluida"
        r.data = {
            "court": result["court"],
            "court_label": _datajud_court_label(result["court"]),
            "endpoint": result["endpoint"],
            "request": result["request"],
            "total": result["total"],
            "count": len(result["hits"]),
            "next_search_after": result["next_search_after"],
            "hits": normalized_hits,
        }
    except Exception as exc:
        r.make_error(0, "Erro ao consultar DataJud", str(exc))
    return r


def seed_default_court_connectors(session_payload: dict, payload: dict) -> NXResult:
    r = NXResult()
    if not _has_permission(session_payload, "integrations.write"):
        r.make_error(403, "Permissao insuficiente para cadastrar conectores de tribunais")
        return r

    sync_endpoint = payload.get("sync_endpoint") or payload.get("base_url") or appConfig.localCourtBridgeUrl
    requested = payload.get("courts") or payload.get("court_codes") or []
    courts = [_court_slug(item) for item in requested] if isinstance(requested, list) and requested else sorted(DATAJUD_COURTS)
    courts = [court for court in courts if court in DATAJUD_COURTS]
    if not courts:
        r.make_error(0, "Nenhum tribunal valido informado para cadastro")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        created = 0
        updated = 0
        records = []
        for court in courts:
            connector = _default_connector_payload(court, sync_endpoint)
            nx.xp_nx.execute(
                """
                SELECT id
                FROM court_connectors
                WHERE company_id = %s AND court_code = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (session_payload["company_id"], connector["court_code"]),
            )
            existing = nx.xp_nx.fetchone()
            if existing:
                nx.xp_nx.execute(
                    """
                    UPDATE court_connectors
                    SET court_name = %s,
                        court_system = %s,
                        base_url = %s,
                        status = %s,
                        supports_public_lookup = %s,
                        supports_certificate = %s,
                        settings = %s::jsonb,
                        updated_at = NOW(),
                        deleted_at = NULL
                    WHERE id = %s
                    RETURNING id, court_code, court_name, court_system, base_url, status
                    """,
                    (
                        connector["court_name"],
                        connector["court_system"],
                        connector["base_url"],
                        connector["status"],
                        connector["supports_public_lookup"],
                        connector["supports_certificate"],
                        _json(connector["settings"]),
                        existing["id"],
                    ),
                )
                updated += 1
                row = nx.xp_nx.fetchone()
                records.append(dict(row))
            else:
                nx.xp_nx.execute(
                    """
                    INSERT INTO court_connectors (
                        company_id, court_code, court_name, court_system, base_url, status,
                        supports_public_lookup, supports_certificate, settings
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    RETURNING id, court_code, court_name, court_system, base_url, status
                    """,
                    (
                        session_payload["company_id"],
                        connector["court_code"],
                        connector["court_name"],
                        connector["court_system"],
                        connector["base_url"],
                        connector["status"],
                        connector["supports_public_lookup"],
                        connector["supports_certificate"],
                        _json(connector["settings"]),
                    ),
                )
                created += 1
                records.append(dict(nx.xp_nx.fetchone()))

        nx.conn_nx.commit()
        register_audit_log(
            session_payload["company_id"],
            session_payload.get("user_id"),
            "court_connectors",
            None,
            "seed_defaults",
            None,
            {"created": created, "updated": updated, "sync_endpoint": sync_endpoint, "courts": courts},
        )
        r.status = True
        r.message = "Conectores padrao dos tribunais cadastrados"
        r.data = {"created": created, "updated": updated, "total": len(records), "sync_endpoint": sync_endpoint, "records": records}
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao cadastrar conectores dos tribunais", str(exc))
    finally:
        nx.stop()

    return r


def list_certificate_agents_status(session_payload: dict, payload: dict | None = None) -> NXResult:
    r = NXResult()
    if not _has_permission(session_payload, "integrations.read"):
        r.make_error(403, "Permissao insuficiente para listar agentes locais")
        return r

    payload = payload or {}
    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            """
            SELECT id, name, agent_key, status, metadata, last_seen_at, created_at, updated_at,
                   CASE
                     WHEN last_seen_at IS NULL THEN 'never_seen'
                     WHEN last_seen_at < NOW() - INTERVAL '2 minutes' THEN 'offline'
                     ELSE 'online'
                   END AS runtime_status
            FROM certificate_agents
            WHERE company_id = %s AND deleted_at IS NULL
            ORDER BY COALESCE(last_seen_at, created_at) DESC
            LIMIT %s
            """,
            (session_payload["company_id"], min(_safe_int(payload.get("limit"), 50), 100)),
        )
        rows = [dict(row) for row in nx.xp_nx.fetchall()]
        r.status = True
        r.message = "Agentes locais carregados"
        r.data = rows
    except Exception as exc:
        r.make_error(0, "Erro ao listar agentes locais", str(exc))
    finally:
        nx.stop()
    return r


def list_certificate_agent_jobs_status(session_payload: dict, payload: dict | None = None) -> NXResult:
    r = NXResult()
    if not _has_permission(session_payload, "sync.read"):
        r.make_error(403, "Permissao insuficiente para listar jobs dos agentes")
        return r

    payload = payload or {}
    params = [session_payload["company_id"]]
    filters = ["j.company_id = %s", "j.deleted_at IS NULL"]
    if payload.get("status"):
        filters.append("j.status = %s")
        params.append(payload.get("status"))
    if payload.get("agent_key"):
        filters.append("j.assigned_agent_key = %s")
        params.append(payload.get("agent_key"))
    if payload.get("case_id"):
        filters.append("j.case_id = %s")
        params.append(payload.get("case_id"))
    params.append(min(_safe_int(payload.get("limit"), 50), 100))

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        nx.xp_nx.execute(
            f"""
            SELECT j.id, j.case_id, c.case_number, c.title AS case_title,
                   j.lawyer_id, l.name AS lawyer_name,
                   j.certificate_id, lc.certificate_name, lc.certificate_access_mode,
                   j.connector_id, cc.court_code, cc.court_name, cc.court_system,
                   j.agent_id, ca.name AS agent_name, j.assigned_agent_key,
                   j.job_type, j.status, j.error_message, j.locked_at, j.completed_at,
                   j.created_at, j.updated_at
            FROM certificate_agent_jobs j
            LEFT JOIN cases c ON c.id = j.case_id
            LEFT JOIN lawyers l ON l.id = j.lawyer_id
            LEFT JOIN lawyer_certificates lc ON lc.id = j.certificate_id
            LEFT JOIN court_connectors cc ON cc.id = j.connector_id
            LEFT JOIN certificate_agents ca ON ca.id = j.agent_id
            WHERE {' AND '.join(filters)}
            ORDER BY j.created_at DESC
            LIMIT %s
            """,
            tuple(params),
        )
        rows = [dict(row) for row in nx.xp_nx.fetchall()]
        r.status = True
        r.message = "Jobs dos agentes carregados"
        r.data = rows
    except Exception as exc:
        r.make_error(0, "Erro ao listar jobs dos agentes", str(exc))
    finally:
        nx.stop()
    return r


def local_court_bridge_manifest(session_payload: dict) -> NXResult:
    r = NXResult()
    if not _has_permission(session_payload, "integrations.read"):
        r.make_error(403, "Permissao insuficiente para consultar ponte local")
        return r

    r.status = True
    r.message = "Manifesto da ponte local carregado"
    r.data = {
        "default_endpoint": appConfig.localCourtBridgeUrl,
        "health_endpoint": appConfig.localCourtBridgeUrl.replace("/tribunal-sync", "/health"),
        "job_endpoint": "/api/v1/certificate-agents/jobs/next",
        "completion_endpoint": "/api/v1/certificate-agents/jobs/<job_id>/complete",
        "supported_certificate_modes": ["file_a1", "token_a3_local", "cloud_provider"],
        "supported_system_families": [
            "pje_trabalhista",
            "pje_federal",
            "pje_eleitoral",
            "pje_militar",
            "tribunal_local_bridge",
            "stj",
            "stm",
        ],
        "required_local_components": [
            "certificate_agent",
            "local_court_bridge",
            "driver do certificado A1/A3 instalado no computador autorizado",
            "navegador/driver do sistema do tribunal quando exigido",
        ],
        "notes": (
            "A ponte local roda fora do Railway para acessar certificados A3 em token/pen drive "
            "e certificados A1 guardados localmente. Ela recebe jobs auditados, consulta o tribunal "
            "correto e devolve documentos/movimentos para importacao."
        ),
    }
    return r


def register_certificate_agent(session_payload: dict, payload: dict) -> NXResult:
    r = NXResult()
    if not _has_permission(session_payload, "integrations.write"):
        r.make_error(403, "Permissao insuficiente para registrar agente")
        return r

    name = str(payload.get("name") or "Agente local A3").strip()
    agent_key = str(payload.get("agent_key") or _court_slug(name) or f"agent-{secrets.token_hex(4)}").strip()
    token = secrets.token_urlsafe(32)
    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened
    try:
        nx.xp_nx.execute(
            """
            INSERT INTO certificate_agents (company_id, name, agent_key, token_hash, status, metadata, created_by)
            VALUES (%s, %s, %s, %s, 'active', %s::jsonb, %s)
            RETURNING id, name, agent_key, status, created_at
            """,
            (
                session_payload["company_id"],
                name,
                agent_key,
                _hash_agent_token(token),
                _json(payload.get("metadata") or {}),
                session_payload.get("user_id"),
            ),
        )
        row = dict(nx.xp_nx.fetchone())
        nx.conn_nx.commit()
        register_audit_log(session_payload["company_id"], session_payload.get("user_id"), "certificate_agents", str(row["id"]), "register", None, {"agent_key": agent_key})
        row["agent_token"] = token
        r.status = True
        r.message = "Agente local registrado. Guarde o token, ele nao sera exibido novamente."
        r.data = row
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao registrar agente local", str(exc))
    finally:
        nx.stop()
    return r


def _load_certificate_agent(nx, token: str) -> dict | None:
    nx.xp_nx.execute(
        """
        SELECT id, company_id, name, agent_key, status
        FROM certificate_agents
        WHERE token_hash = %s AND status IN ('active', 'online') AND deleted_at IS NULL
        LIMIT 1
        """,
        (_hash_agent_token(token),),
    )
    agent = nx.xp_nx.fetchone()
    return dict(agent) if agent else None


def certificate_agent_heartbeat(token: str, payload: dict) -> NXResult:
    r = NXResult()
    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened
    try:
        agent = _load_certificate_agent(nx, token)
        if not agent:
            r.make_error(401, "Agente nao autorizado")
            return r
        nx.xp_nx.execute(
            """
            UPDATE certificate_agents
            SET status = 'online', last_seen_at = NOW(), metadata = COALESCE(metadata, '{}'::jsonb) || %s::jsonb, updated_at = NOW()
            WHERE id = %s
            RETURNING id, name, agent_key, status, last_seen_at
            """,
            (_json(payload.get("metadata") or {}), agent["id"]),
        )
        row = dict(nx.xp_nx.fetchone())
        nx.conn_nx.commit()
        r.status = True
        r.message = "Agente online"
        r.data = row
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro no heartbeat do agente", str(exc))
    finally:
        nx.stop()
    return r


def certificate_agent_next_job(token: str) -> NXResult:
    r = NXResult()
    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened
    try:
        agent = _load_certificate_agent(nx, token)
        if not agent:
            r.make_error(401, "Agente nao autorizado")
            return r
        nx.xp_nx.execute(
            """
            UPDATE certificate_agents
            SET status = 'online', last_seen_at = NOW(), updated_at = NOW()
            WHERE id = %s
            """,
            (agent["id"],),
        )
        nx.xp_nx.execute(
            """
            UPDATE certificate_agent_jobs
            SET status = 'running', agent_id = %s, locked_at = NOW(), updated_at = NOW()
            WHERE id = (
                SELECT id
                FROM certificate_agent_jobs
                WHERE company_id = %s
                  AND deleted_at IS NULL
                  AND status = 'pending'
                  AND (agent_id = %s OR assigned_agent_key = %s)
                ORDER BY created_at ASC
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            RETURNING id, case_id, lawyer_id, certificate_id, connector_id, assigned_agent_key,
                      job_type, status, request_payload, created_at
            """,
            (agent["id"], agent["company_id"], agent["id"], agent["agent_key"]),
        )
        job = nx.xp_nx.fetchone()
        nx.conn_nx.commit()
        r.status = True
        r.message = "Job carregado" if job else "Nenhum job pendente"
        r.data = dict(job) if job else None
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao carregar job do agente", str(exc))
    finally:
        nx.stop()
    return r


def certificate_agent_complete_job(token: str, job_id: str, payload: dict) -> NXResult:
    r = NXResult()
    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened
    try:
        agent = _load_certificate_agent(nx, token)
        if not agent:
            r.make_error(401, "Agente nao autorizado")
            return r
        nx.xp_nx.execute(
            """
            SELECT id, company_id, case_id, lawyer_id, certificate_id, connector_id, assigned_agent_key, request_payload
            FROM certificate_agent_jobs
            WHERE id = %s AND company_id = %s AND deleted_at IS NULL
              AND (agent_id = %s OR assigned_agent_key = %s)
            LIMIT 1
            """,
            (job_id, agent["company_id"], agent["id"], agent["agent_key"]),
        )
        job = nx.xp_nx.fetchone()
        if not job:
            r.make_error(404, "Job nao localizado para este agente")
            return r

        status = "failed" if payload.get("error") else "completed"
        response_payload = payload.get("response") or payload
        documents = response_payload.get("documents") or []
        movements = response_payload.get("movements") or []
        imported_documents = imported_movements = 0
        if status == "completed":
            imported_documents, imported_movements = _replace_tribunal_imports(nx, agent["company_id"], str(job["case_id"]), documents, movements)

        nx.xp_nx.execute(
            """
            UPDATE certificate_agent_jobs
            SET status = %s, response_payload = %s::jsonb, error_message = %s,
                completed_at = NOW(), updated_at = NOW()
            WHERE id = %s
            RETURNING id, status, completed_at
            """,
            (status, _json(response_payload), payload.get("error"), job_id),
        )
        updated_job = dict(nx.xp_nx.fetchone())
        log_payload = {
            "lawyer_id": str(job["lawyer_id"]) if job.get("lawyer_id") else None,
            "court_system": (job.get("request_payload") or {}).get("body", {}).get("court_system"),
            "documents_found": len(documents),
            "documents_downloaded": imported_documents,
            "movements_imported": imported_movements,
        }
        log_row = _insert_sync_log(
            nx,
            {"company_id": agent["company_id"], "user_id": None},
            str(job["case_id"]),
            "tribunal",
            log_payload,
            {"agent_id": str(agent["id"]), "agent_job_id": str(job["id"]), "response": response_payload},
            "success" if status == "completed" else "error",
            payload.get("error"),
        )
        nx.conn_nx.commit()
        register_audit_log(agent["company_id"], None, "certificate_agent_jobs", str(job_id), status, None, {"sync_log_id": str(log_row["id"])})
        r.status = True
        r.message = "Job concluido e importado" if status == "completed" else "Job finalizado com erro"
        r.data = {"job": updated_job, "log": dict(log_row), "documents_imported": imported_documents, "movements_imported": imported_movements}
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao concluir job do agente", str(exc))
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
                SET reviewed = TRUE,
                    text = %s,
                    speaker_label = COALESCE(NULLIF(%s, ''), speaker_label),
                    updated_at = NOW()
                WHERE id = %s AND transcription_id = %s AND company_id = %s
                """,
                (
                    reviewed_text,
                    payload.get("speaker_label"),
                    payload.get("segment_id"),
                    transcription_id,
                    session_payload["company_id"],
                ),
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


def _seconds_from_timestamp(value: str | None, fallback: int = 0) -> int:
    if not value:
        return fallback
    parts = [part for part in str(value).strip().split(":") if part != ""]
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(float(parts[2]))
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(float(parts[1]))
        return int(float(parts[0]))
    except (TypeError, ValueError):
        return fallback


def _format_seconds(value) -> str:
    total = _safe_int(value)
    hours = total // 3600
    minutes = (total % 3600) // 60
    seconds = total % 60
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def _parse_manual_line(line: str, index: int) -> dict | None:
    clean = str(line or "").strip()
    if not clean:
        return None

    pattern = re.compile(
        r"^(?:\[(?P<bracket_time>\d{1,2}:\d{2}(?::\d{2})?)\]\s*)?"
        r"(?:(?P<plain_time>\d{1,2}:\d{2}(?::\d{2})?)\s+)?"
        r"(?P<speaker>[A-Za-zÀ-ÿ0-9 ._'/-]{2,80})\s*(?:[:\-–—])\s*(?P<text>.+)$"
    )
    match = pattern.match(clean)
    if match:
        timestamp = match.group("bracket_time") or match.group("plain_time")
        start = _seconds_from_timestamp(timestamp, index * 30)
        return {
            "speaker_label": match.group("speaker").strip(),
            "start_seconds": start,
            "end_seconds": start + 30,
            "text": match.group("text").strip(),
            "confidence_score": 1,
        }

    continuation_pattern = re.compile(r"^(?:\[(?P<bracket_time>\d{1,2}:\d{2}(?::\d{2})?)\]\s*)?(?P<text>.+)$")
    continuation = continuation_pattern.match(clean)
    timestamp = continuation.group("bracket_time") if continuation else None
    start = _seconds_from_timestamp(timestamp, index * 30)
    return {
        "speaker_label": "Fala sem identificação",
        "start_seconds": start,
        "end_seconds": start + 30,
        "text": continuation.group("text").strip() if continuation else clean,
        "confidence_score": 1,
    }


def _segment_text(text: str) -> list[dict]:
    raw_text = str(text or "").strip()
    if not raw_text:
        return []

    raw_text = re.sub(
        r"\s+(?=(?:\[\d{1,2}:\d{2}(?::\d{2})?\]\s*)?[A-Za-zÀ-ÿ0-9 ._'/-]{2,80}\s*[:\-–—]\s+)",
        "\n",
        raw_text,
    )
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    parsed_lines = [_parse_manual_line(line, index) for index, line in enumerate(lines)]
    parsed_lines = [line for line in parsed_lines if line]

    speaker_like_count = sum(1 for item in parsed_lines if item["speaker_label"] != "Fala sem identificação")
    if parsed_lines and (speaker_like_count or len(parsed_lines) > 1):
        merged = []
        for item in parsed_lines:
            if (
                item["speaker_label"] == "Fala sem identificação"
                and merged
                and not re.match(r"^\d{1,2}:\d{2}", item["text"])
            ):
                merged[-1]["text"] = f"{merged[-1]['text']}\n{item['text']}"
                merged[-1]["end_seconds"] = max(_safe_int(merged[-1]["end_seconds"]), _safe_int(item["end_seconds"]))
            else:
                merged.append(item)
        return merged

    chunks = [part.strip() for part in re.split(r"(?<=[.!?])\s+", raw_text) if part.strip()]
    return [
        {
            "speaker_label": "Fala sem identificação",
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


def _format_transcription_text(transcription: dict, segments: list[dict], summary_data: dict | None = None) -> str:
    summary_data = summary_data or _build_transcription_summary(segments)
    lines = [
        f"Transcrição: {transcription.get('title') or 'Sem título'}",
        f"Tipo: {transcription.get('transcription_type') or '-'}",
        f"Idioma: {transcription.get('language') or 'pt-BR'}",
        "",
        "Resumo",
        summary_data["summary"],
        "",
        "Pontos-chave",
    ]
    lines.extend(f"- {item}" for item in summary_data["key_points"])
    lines.extend(["", "Próximos passos"])
    lines.extend(f"- {item}" for item in summary_data["next_steps"])
    lines.extend(["", "Riscos e cuidados"])
    lines.extend(f"- {item}" for item in summary_data["risks"])
    lines.extend(["", "Transcrição completa"])
    for segment in segments:
        start = _format_seconds(segment.get("start_seconds"))
        end = _format_seconds(segment.get("end_seconds"))
        speaker = segment.get("speaker_label") or "Fala sem identificação"
        lines.append(f"[{start} - {end}] {speaker}:")
        lines.append(str(segment.get("text") or "").strip())
        lines.append("")
    return "\n".join(lines).strip()


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


def _load_transcription_with_segments(nx, transcription_id: str, company_id: str) -> tuple[dict | None, list[dict]]:
    nx.xp_nx.execute(
        """
        SELECT id, company_id, client_id, case_id, appointment_id, title, source, transcription_type,
               status, language, quality_score, confidentiality, created_by, finalized_at, created_at
        FROM transcriptions
        WHERE id = %s AND company_id = %s AND deleted_at IS NULL
        """,
        (transcription_id, company_id),
    )
    transcription = nx.xp_nx.fetchone()
    if not transcription:
        return None, []

    nx.xp_nx.execute(
        """
        SELECT id, transcription_id, speaker_label, start_seconds, end_seconds, text, confidence_score, reviewed, created_at, updated_at
        FROM transcription_segments
        WHERE transcription_id = %s AND company_id = %s AND deleted_at IS NULL
        ORDER BY start_seconds NULLS LAST, created_at ASC
        """,
        (transcription_id, company_id),
    )
    return dict(transcription), [dict(row) for row in nx.xp_nx.fetchall()]


def export_transcription_note(transcription_id: str, session_payload: dict, payload: dict) -> NXResult:
    r = NXResult()
    if not _has_permission(session_payload, "notes.write"):
        r.make_error(403, "Permissão insuficiente para gerar anotação da transcrição")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        transcription, segments = _load_transcription_with_segments(nx, transcription_id, session_payload["company_id"])
        if not transcription:
            r.make_error(404, "Transcrição não localizada")
            return r
        if not segments:
            r.make_error(0, "A transcrição ainda não possui falas processadas")
            return r

        summary_data = _build_transcription_summary(segments)
        full_content = _format_transcription_text(transcription, segments, summary_data)
        note_content = payload.get("content") or full_content
        nx.xp_nx.execute(
            """
            INSERT INTO notes (company_id, client_id, case_id, appointment_id, title, content, type, visibility, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, 'transcription', %s, %s)
            RETURNING id, title, type, visibility, created_at
            """,
            (
                session_payload["company_id"],
                transcription.get("client_id"),
                transcription.get("case_id"),
                transcription.get("appointment_id"),
                payload.get("title") or f"Anotação da transcrição - {transcription.get('title')}",
                note_content,
                payload.get("visibility") or transcription.get("confidentiality") or "internal",
                session_payload.get("user_id"),
            ),
        )
        row = nx.xp_nx.fetchone()
        nx.conn_nx.commit()
        register_audit_log(session_payload["company_id"], session_payload.get("user_id"), "transcriptions", transcription_id, "export_note", None, {"note_id": str(row["id"])})
        r.status = True
        r.message = "Anotação gerada a partir da transcrição"
        r.data = dict(row)
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao gerar anotação da transcrição", str(exc))
    finally:
        nx.stop()

    return r


def export_transcription_document(transcription_id: str, session_payload: dict, payload: dict) -> NXResult:
    r = NXResult()
    if not _has_permission(session_payload, "documents.write"):
        r.make_error(403, "Permissão insuficiente para gerar documento da transcrição")
        return r

    nx = NXDatabaseConnection()
    opened = nx.active()
    if opened.error:
        return opened

    try:
        transcription, segments = _load_transcription_with_segments(nx, transcription_id, session_payload["company_id"])
        if not transcription:
            r.make_error(404, "Transcrição não localizada")
            return r
        if not segments:
            r.make_error(0, "A transcrição ainda não possui falas processadas")
            return r

        summary_data = _build_transcription_summary(segments)
        full_content = _format_transcription_text(transcription, segments, summary_data)
        context = {
            "source": "transcription",
            "transcription": transcription,
            "summary": summary_data,
            "content": full_content,
            "segments": segments,
            "format": "structured_text",
        }
        nx.xp_nx.execute(
            """
            INSERT INTO generated_documents (company_id, client_id, case_id, title, output_format, context, status, generated_by)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, 'generated', %s)
            RETURNING id, title, output_format, status, created_at
            """,
            (
                session_payload["company_id"],
                transcription.get("client_id"),
                transcription.get("case_id"),
                payload.get("title") or f"Documento de transcrição - {transcription.get('title')}",
                payload.get("output_format") or "html",
                _json(context),
                session_payload.get("user_id"),
            ),
        )
        row = nx.xp_nx.fetchone()
        nx.conn_nx.commit()
        register_audit_log(session_payload["company_id"], session_payload.get("user_id"), "transcriptions", transcription_id, "export_document", None, {"generated_document_id": str(row["id"])})
        r.status = True
        r.message = "Documento gerado a partir da transcrição"
        r.data = dict(row)
    except Exception as exc:
        nx.conn_nx.rollback()
        r.make_error(0, "Erro ao gerar documento da transcrição", str(exc))
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

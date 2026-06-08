from source.app import app
from source.core.system.utils import NXResult, get_session_payload
from source.logic.orb_reports import case_ai_insights, client_ai_insights, communication_ai_insights, dashboard_ai_insights, document_ai_insights, financial_summary, operational_bi, operational_summary, operational_timeline


@app.route("/api/v1/reports/summary", methods=["GET"])
def reports_summary():
    try:
        session_payload = get_session_payload()
    except Exception as exc:
        r = NXResult()
        r.make_error(401, "Falha na autenticacao", str(exc))
        return r.toJSON(), 401

    r = operational_summary(session_payload)
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/reports/timeline", methods=["GET"])
def reports_timeline():
    try:
        session_payload = get_session_payload()
    except Exception as exc:
        r = NXResult()
        r.make_error(401, "Falha na autenticacao", str(exc))
        return r.toJSON(), 401

    r = operational_timeline(session_payload)
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/reports/bi", methods=["GET"])
def reports_bi():
    try:
        session_payload = get_session_payload()
    except Exception as exc:
        r = NXResult()
        r.make_error(401, "Falha na autenticacao", str(exc))
        return r.toJSON(), 401

    r = operational_bi(session_payload)
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/reports/financial-summary", methods=["GET"])
def reports_financial_summary():
    try:
        session_payload = get_session_payload()
    except Exception as exc:
        r = NXResult()
        r.make_error(401, "Falha na autenticacao", str(exc))
        return r.toJSON(), 401

    r = financial_summary(session_payload)
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/ai/case-insights/<case_id>", methods=["GET"])
def ai_case_insights(case_id):
    try:
        session_payload = get_session_payload()
    except Exception as exc:
        r = NXResult()
        r.make_error(401, "Falha na autenticacao", str(exc))
        return r.toJSON(), 401

    r = case_ai_insights(case_id, session_payload)
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/ai/document-insights/<document_id>", methods=["GET"])
def ai_document_insights(document_id):
    try:
        session_payload = get_session_payload()
    except Exception as exc:
        r = NXResult()
        r.make_error(401, "Falha na autenticacao", str(exc))
        return r.toJSON(), 401

    r = document_ai_insights(document_id, session_payload)
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/ai/client-insights/<client_id>", methods=["GET"])
def ai_client_insights(client_id):
    try:
        session_payload = get_session_payload()
    except Exception as exc:
        r = NXResult()
        r.make_error(401, "Falha na autenticacao", str(exc))
        return r.toJSON(), 401

    r = client_ai_insights(client_id, session_payload)
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/ai/dashboard-insights", methods=["GET"])
def ai_dashboard_insights():
    try:
        session_payload = get_session_payload()
    except Exception as exc:
        r = NXResult()
        r.make_error(401, "Falha na autenticacao", str(exc))
        return r.toJSON(), 401

    r = dashboard_ai_insights(session_payload)
    return r.toJSON(), (200 if r.status else 400)


@app.route("/api/v1/ai/communication-insights/<message_id>", methods=["GET"])
def ai_communication_insights(message_id):
    try:
        session_payload = get_session_payload()
    except Exception as exc:
        r = NXResult()
        r.make_error(401, "Falha na autenticacao", str(exc))
        return r.toJSON(), 401

    r = communication_ai_insights(message_id, session_payload)
    return r.toJSON(), (200 if r.status else 400)

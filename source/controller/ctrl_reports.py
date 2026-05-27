from source.app import app
from source.core.system.utils import NXResult, get_session_payload
from source.logic.orb_reports import operational_summary, operational_timeline


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

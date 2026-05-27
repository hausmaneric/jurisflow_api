from source.app import app
from source.core.system.utils import NXResult, get_session_payload
from source.logic.orb_crud import list_resource


@app.route("/api/v1/catalog", methods=["GET"])
def catalog():
    try:
        session_payload = get_session_payload()
    except Exception as exc:
        r = NXResult()
        r.make_error(401, "Falha na autenticacao", str(exc))
        return r.toJSON(), 401

    payload = {}
    for resource in ("permissions", "roles", "message_templates", "document_templates"):
        result = list_resource(resource, session_payload)
        if result.status:
            payload[resource] = result.data
        else:
            payload[resource] = []

    r = NXResult()
    r.status = True
    r.message = "Catalogo carregado com sucesso"
    r.data = payload
    return r.toJSON()

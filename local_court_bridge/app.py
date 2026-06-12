import importlib
import os
from datetime import datetime, timezone

from flask import Flask, jsonify, request


app = Flask(__name__)

BRIDGE_TOKEN = os.getenv("JURISFLOW_LOCAL_BRIDGE_TOKEN", "")
DEFAULT_DRIVER = os.getenv("JURISFLOW_LOCAL_BRIDGE_DEFAULT_DRIVER", "unsupported")


def _auth_ok() -> bool:
    if not BRIDGE_TOKEN:
        return True
    header = request.headers.get("Authorization", "")
    return header == f"Bearer {BRIDGE_TOKEN}"


def _system_family(court_system: str, certificate: dict) -> str:
    metadata = certificate.get("metadata") or {}
    requested = metadata.get("system_family") or court_system or DEFAULT_DRIVER
    value = str(requested or "").strip().lower()
    if value.startswith("trt"):
        return "pje"
    if value.startswith("trf"):
        return "pje"
    if value.startswith("tj"):
        return os.getenv("JURISFLOW_LOCAL_BRIDGE_TJ_DRIVER", DEFAULT_DRIVER)
    if value in {"pje_trabalhista", "pje_federal", "pje_eleitoral", "pje_militar"}:
        return "pje"
    return value or DEFAULT_DRIVER


def _load_driver(driver_name: str):
    safe_name = "".join(ch for ch in driver_name if ch.isalnum() or ch == "_")
    if not safe_name:
        safe_name = "unsupported"
    module = importlib.import_module(f"drivers.{safe_name}")
    return module.CourtDriver()


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "service": "jurisflow-local-court-bridge",
            "time": datetime.now(timezone.utc).isoformat(),
            "auth_required": bool(BRIDGE_TOKEN),
            "default_driver": DEFAULT_DRIVER,
        }
    )


@app.post("/tribunal-sync")
def tribunal_sync():
    if not _auth_ok():
        return jsonify({"error": "unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    case_number = str(payload.get("case_number") or "").strip()
    certificate = payload.get("certificate") or {}
    court_system = str(payload.get("court_system") or "").strip().lower()

    if len("".join(ch for ch in case_number if ch.isdigit())) != 20:
        return jsonify({"error": "case_number precisa ter 20 digitos CNJ"}), 400
    if not certificate.get("access_mode"):
        return jsonify({"error": "certificate.access_mode e obrigatorio"}), 400

    driver_name = _system_family(court_system, certificate)
    try:
        driver = _load_driver(driver_name)
        result = driver.sync_case(payload)
    except ModuleNotFoundError:
        return jsonify(
            {
                "error": f"Driver local '{driver_name}' nao encontrado",
                "driver": driver_name,
                "hint": "Instale ou implemente o driver em local_court_bridge/drivers para o sistema deste tribunal.",
            }
        ), 501
    except NotImplementedError as exc:
        return jsonify(
            {
                "error": str(exc),
                "driver": driver_name,
                "hint": "Este tribunal exige automacao local/certificado instalado no computador autorizado.",
            }
        ), 501
    except Exception as exc:
        return jsonify({"error": str(exc), "driver": driver_name}), 500

    documents = result.get("documents") or []
    movements = result.get("movements") or []
    return jsonify(
        {
            "status": "completed",
            "driver": driver_name,
            "case_number": case_number,
            "documents": documents,
            "movements": movements,
            "raw": result.get("raw") or {},
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "8765")))

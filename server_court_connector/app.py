import importlib
import os
from datetime import datetime, timezone

from flask import Flask, jsonify, request


app = Flask(__name__)

CONNECTOR_TOKEN = os.getenv("JURISFLOW_SERVER_COURT_CONNECTOR_TOKEN", "")
DEFAULT_DRIVER = os.getenv("JURISFLOW_SERVER_COURT_DEFAULT_DRIVER", "unsupported")


def _auth_ok() -> bool:
    if not CONNECTOR_TOKEN:
        return True
    return request.headers.get("Authorization", "") == f"Bearer {CONNECTOR_TOKEN}"


def _digits(value: str) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _driver_name(payload: dict) -> str:
    certificate = payload.get("certificate") or {}
    metadata = certificate.get("metadata") or {}
    requested = payload.get("court_system") or metadata.get("system_family") or DEFAULT_DRIVER
    value = str(requested or "").lower().strip()
    if value.startswith(("trt", "trf")) or value.startswith("pje_"):
        return "pje"
    if value.startswith("tj"):
        return os.getenv("JURISFLOW_SERVER_TJ_DRIVER", DEFAULT_DRIVER)
    return value or DEFAULT_DRIVER


def _load_driver(name: str):
    safe_name = "".join(ch for ch in name if ch.isalnum() or ch == "_") or "unsupported"
    module = importlib.import_module(f"drivers.{safe_name}")
    return module.CourtDriver()


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "service": "jurisflow-server-court-connector",
            "time": datetime.now(timezone.utc).isoformat(),
            "auth_required": bool(CONNECTOR_TOKEN),
            "default_driver": DEFAULT_DRIVER,
        }
    )


@app.post("/tribunal-sync")
def tribunal_sync():
    if not _auth_ok():
        return jsonify({"error": "unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    certificate = payload.get("certificate") or {}
    access_mode = certificate.get("access_mode")
    if _digits(payload.get("case_number")).__len__() != 20:
        return jsonify({"error": "case_number precisa ter 20 digitos CNJ"}), 400
    if access_mode not in {"file_a1", "cloud_provider"}:
        return jsonify(
            {
                "error": f"Modo {access_mode or 'nao informado'} nao suportado no conector remoto",
                "hint": "Use A1 por arquivo seguro ou certificado em nuvem. A3 USB exige ponte local.",
            }
        ), 400

    driver_name = _driver_name(payload)
    try:
        driver = _load_driver(driver_name)
        result = driver.sync_case(payload)
    except ModuleNotFoundError:
        return jsonify({"error": f"Driver remoto '{driver_name}' nao encontrado", "driver": driver_name}), 501
    except NotImplementedError as exc:
        return jsonify({"error": str(exc), "driver": driver_name}), 501
    except Exception as exc:
        return jsonify({"error": str(exc), "driver": driver_name}), 500

    return jsonify(
        {
            "status": "completed",
            "driver": driver_name,
            "case_number": payload.get("case_number"),
            "documents": result.get("documents") or [],
            "movements": result.get("movements") or [],
            "raw": result.get("raw") or {},
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8082")))

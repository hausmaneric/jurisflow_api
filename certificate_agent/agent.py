import os
import time

import requests


API_URL = os.getenv("JURISFLOW_API_URL", "https://web-production-3c57a.up.railway.app/api/v1").rstrip("/")
TOKEN = os.getenv("CERTIFICATE_AGENT_TOKEN", "")
INTERVAL_SECONDS = int(os.getenv("CERTIFICATE_AGENT_INTERVAL_SECONDS", "10"))


def _headers() -> dict:
    if not TOKEN:
        raise RuntimeError("CERTIFICATE_AGENT_TOKEN nao configurado")
    return {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def heartbeat() -> None:
    requests.post(
        f"{API_URL}/certificate-agents/heartbeat",
        headers=_headers(),
        json={"metadata": {"runtime": "python", "mode": "polling"}},
        timeout=30,
    ).raise_for_status()


def next_job() -> dict | None:
    response = requests.get(f"{API_URL}/certificate-agents/jobs/next", headers=_headers(), timeout=60)
    response.raise_for_status()
    payload = response.json()
    return payload.get("data")


def complete_job(job_id: str, result: dict) -> None:
    response = requests.post(
        f"{API_URL}/certificate-agents/jobs/{job_id}/complete",
        headers=_headers(),
        json=result,
        timeout=120,
    )
    response.raise_for_status()


def execute_connector(job: dict) -> dict:
    request_payload = job.get("request_payload") or {}
    endpoint = request_payload.get("endpoint")
    if not endpoint:
        raise RuntimeError("Job sem endpoint de conector")

    headers = request_payload.get("headers") or {}
    body = request_payload.get("body") or {}
    response = requests.post(endpoint, headers=headers, json=body, timeout=300)
    if response.status_code >= 400:
        raise RuntimeError(f"Conector retornou HTTP {response.status_code}: {response.text[:500]}")
    return response.json()


def run_once() -> None:
    heartbeat()
    job = next_job()
    if not job:
        return

    try:
        result = execute_connector(job)
    except Exception as exc:
        complete_job(job["id"], {"error": str(exc)})
        return

    complete_job(job["id"], result)


def main() -> None:
    print("JurisFlow Certificate Agent iniciado")
    while True:
        try:
            run_once()
        except Exception as exc:
            print(f"Falha no ciclo do agente: {exc}")
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()

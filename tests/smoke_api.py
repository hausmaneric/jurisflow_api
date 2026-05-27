import json
import os
from urllib import error, request


def call_json(url: str, method: str = "GET", payload: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    body = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    req = request.Request(url, data=body, headers=headers, method=method)
    with request.urlopen(req) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def main() -> int:
    base_url = os.getenv("JURISFLOW_BASE_URL", "http://127.0.0.1:8080").rstrip("/")

    checks = [
        "/api/v1/health",
        "/api/v1/routes",
        "/api/v1/about",
    ]

    for path in checks:
        status, payload = call_json(f"{base_url}{path}")
        if status != 200 or payload.get("status") is not True:
            raise SystemExit(f"Falha no smoke test de {path}: {status} {payload}")
        print(f"OK {path}")

    print("Smoke test basico concluido com sucesso.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except error.URLError as exc:
        raise SystemExit(f"Falha ao acessar API: {exc}")

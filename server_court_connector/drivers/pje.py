import os

import requests


class CourtDriver:
    def sync_case(self, payload: dict) -> dict:
        middleware_url = os.getenv("JURISFLOW_SERVER_PJE_MIDDLEWARE_URL", "").strip()
        if not middleware_url:
            raise NotImplementedError(
                "Configure JURISFLOW_SERVER_PJE_MIDDLEWARE_URL para consultar PJe com A1 seguro ou certificado em nuvem."
            )

        headers = {"Content-Type": "application/json"}
        token = os.getenv("JURISFLOW_SERVER_PJE_MIDDLEWARE_TOKEN", "")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        response = requests.post(
            middleware_url,
            headers=headers,
            json=payload,
            timeout=int(os.getenv("JURISFLOW_SERVER_PJE_TIMEOUT", "300")),
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Middleware PJe retornou HTTP {response.status_code}: {response.text[:500]}")
        data = response.json()
        return {
            "documents": data.get("documents") or [],
            "movements": data.get("movements") or [],
            "raw": data.get("raw") or data,
        }

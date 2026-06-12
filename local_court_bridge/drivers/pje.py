import os


class CourtDriver:
    """Contrato para PJe local.

    O PJe exige certificado instalado no computador do usuario e fluxo web do
    proprio tribunal. Este driver deixa o contrato operacional e impede retorno
    falso quando a automacao local ainda nao foi configurada.
    """

    def sync_case(self, payload: dict) -> dict:
        automation_url = os.getenv("JURISFLOW_PJE_AUTOMATION_URL", "").strip()
        if not automation_url:
            raise NotImplementedError(
                "Configure JURISFLOW_PJE_AUTOMATION_URL apontando para a automacao local do PJe."
            )

        import requests

        response = requests.post(automation_url, json=payload, timeout=int(os.getenv("JURISFLOW_PJE_TIMEOUT", "300")))
        if response.status_code >= 400:
            raise RuntimeError(f"Automacao PJe retornou HTTP {response.status_code}: {response.text[:500]}")
        data = response.json()
        return {
            "documents": data.get("documents") or [],
            "movements": data.get("movements") or [],
            "raw": data.get("raw") or data,
        }

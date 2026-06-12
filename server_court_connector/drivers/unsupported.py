class CourtDriver:
    def sync_case(self, payload: dict) -> dict:
        raise NotImplementedError(
            "Driver remoto do tribunal nao configurado. Configure um driver PJe/e-SAJ/eproc/Projudi ou um middleware contratado."
        )

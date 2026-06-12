class CourtDriver:
    def sync_case(self, payload: dict) -> dict:
        court_system = payload.get("court_system") or "tribunal"
        raise NotImplementedError(
            f"O driver local para {court_system} ainda nao foi configurado neste computador."
        )

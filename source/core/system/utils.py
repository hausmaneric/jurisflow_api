from dataclasses import dataclass, field

from flask import jsonify, request

from source.core.system.security import decode_token


@dataclass
class NXResult:
    status: bool = False
    code: int = 0
    message: str = ""
    error: bool = False
    detail: str = ""
    data: object = field(default_factory=dict)

    def make_error(self, code: int, message: str, detail: str = "") -> None:
        self.status = False
        self.error = True
        self.code = code
        self.message = message
        self.detail = detail

    def toJSON(self):
        payload = {
            "status": self.status,
            "code": self.code,
            "message": self.message,
            "error": self.error,
            "detail": self.detail,
            "data": self.data,
        }
        return jsonify(payload)


def get_bearer_token() -> str:
    header = request.headers.get("Authorization", "").strip()
    if not header.startswith("Bearer "):
        raise ValueError("Header Authorization invalido")
    return header.replace("Bearer ", "", 1).strip()


def get_session_payload() -> dict:
    token = get_bearer_token()
    return decode_token(token)

from datetime import UTC, datetime
from pathlib import Path

from source.core.config.config import appConfig


def dispatch_message(channel: str, recipient: str, subject: str, body: str) -> dict:
    mode = appConfig.messageMode
    if mode == "log":
        target_dir = Path(__file__).resolve().parents[3] / appConfig.storageRoot / "message_logs"
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = target_dir / f"{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}_{channel}.log"
        filename.write_text(
            f"channel={channel}\nrecipient={recipient}\nsubject={subject}\n\n{body}\n",
            encoding="utf-8",
        )
        return {"mode": mode, "status": "sent", "log_file": str(filename)}

    return {"mode": mode, "status": "queued"}

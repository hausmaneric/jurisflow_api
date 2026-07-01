import os
import tempfile
from pathlib import Path

import requests
from flask import Flask, jsonify, request


app = Flask(__name__)

_WHISPER_MODEL = None
_WHISPER_MODEL_KEY = None


def _safe_float(value, fallback=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _auth_ok() -> bool:
    token = os.getenv("WHISPER_WORKER_TOKEN", "")
    if not token:
        return True
    header = request.headers.get("Authorization", "")
    return header == f"Bearer {token}"


def _download_file(file_url: str) -> Path:
    if not file_url:
        raise ValueError("file_url e obrigatorio")
    headers = {}
    token = os.getenv("WHISPER_FILE_DOWNLOAD_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.get(file_url, headers=headers, timeout=120)
    response.raise_for_status()
    suffix = Path(file_url.split("?")[0]).suffix or ".audio"
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    handle.write(response.content)
    handle.close()
    return Path(handle.name)


def _get_whisper_model():
    global _WHISPER_MODEL, _WHISPER_MODEL_KEY

    from faster_whisper import WhisperModel

    model_size = os.getenv("WHISPER_MODEL_SIZE", "medium")
    device = os.getenv("WHISPER_DEVICE", "cpu")
    compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    key = (model_size, device, compute_type)

    if _WHISPER_MODEL is None or _WHISPER_MODEL_KEY != key:
        _WHISPER_MODEL = WhisperModel(model_size, device=device, compute_type=compute_type)
        _WHISPER_MODEL_KEY = key

    return _WHISPER_MODEL


def _transcribe_with_whisper(file_path: Path, payload: dict) -> list[dict]:
    language = (payload.get("language") or "pt-BR").split("-")[0].lower()
    vocabulary = payload.get("vocabulary") or []
    initial_prompt = ", ".join(str(item) for item in vocabulary if item)

    model = _get_whisper_model()
    segments, info = model.transcribe(
        str(file_path),
        language=language,
        beam_size=5,
        vad_filter=True,
        word_timestamps=False,
        initial_prompt=initial_prompt or None,
    )

    normalized = []
    for index, segment in enumerate(segments):
        normalized.append(
            {
                "speaker_label": f"Falante {index + 1}",
                "start_seconds": int(_safe_float(segment.start)),
                "end_seconds": int(_safe_float(segment.end)),
                "text": str(segment.text or "").strip(),
                "confidence_score": max(0.0, min(1.0, 1.0 - _safe_float(getattr(segment, "avg_logprob", 0.0), 0.0) * -0.1)),
            }
        )

    return [item for item in normalized if item["text"]]


def _apply_optional_diarization(file_path: Path, segments: list[dict]) -> list[dict]:
    enabled = os.getenv("WHISPER_ENABLE_DIARIZATION", "false").lower() == "true"
    token = os.getenv("PYANNOTE_AUTH_TOKEN", "")
    if not enabled or not token or not segments:
        return segments

    try:
        from pyannote.audio import Pipeline

        pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", use_auth_token=token)
        diarization = pipeline(str(file_path))
        turns = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            turns.append((int(turn.start), int(turn.end), str(speaker).replace("SPEAKER_", "Falante ")))

        for segment in segments:
            midpoint = int((segment["start_seconds"] + segment["end_seconds"]) / 2)
            label = next((speaker for start, end, speaker in turns if start <= midpoint <= end), None)
            if label:
                segment["speaker_label"] = label
    except Exception as exc:  # diarizacao nao deve derrubar a transcricao
        for segment in segments:
            segment["diarization_warning"] = str(exc)[:240]
    return segments


@app.get("/health")
def health():
    return jsonify({"status": "ok", "provider": "faster-whisper"})


@app.get("/ready")
def ready():
    return jsonify(
        {
            "status": "ready",
            "provider": "faster-whisper",
            "model_size": os.getenv("WHISPER_MODEL_SIZE", "medium"),
            "device": os.getenv("WHISPER_DEVICE", "cpu"),
            "compute_type": os.getenv("WHISPER_COMPUTE_TYPE", "int8"),
            "diarization": os.getenv("WHISPER_ENABLE_DIARIZATION", "false").lower() == "true",
        }
    )


@app.post("/transcribe")
def transcribe():
    if not _auth_ok():
        return jsonify({"error": "unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    file_path = None
    try:
        file_path = _download_file(payload.get("file_url"))
        segments = _transcribe_with_whisper(file_path, payload)
        segments = _apply_optional_diarization(file_path, segments)
        return jsonify({"segments": segments, "provider": "faster-whisper"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        if file_path and file_path.exists():
            file_path.unlink(missing_ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8081")))

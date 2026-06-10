# JurisFlow Transcription Worker

Worker HTTP sem OpenAI para transcricao automatica de audios e videos.

## Como funciona

- Endpoint: `POST /transcribe`
- Autenticacao opcional: `Authorization: Bearer <WHISPER_WORKER_TOKEN>`
- Entrada principal: `file_url`, `language`, `vocabulary`
- Saida: segmentos com `speaker_label`, `start_seconds`, `end_seconds`, `text` e `confidence_score`

Por padrao o worker usa `faster-whisper`. Se `PYANNOTE_AUTH_TOKEN` e
`WHISPER_ENABLE_DIARIZATION=true` forem configurados, ele tenta diarizacao com
Pyannote para separar falantes. Sem diarizacao, os segmentos sao entregues como
`Falante 1` para revisao humana na plataforma.

## Variaveis

```env
WHISPER_MODEL_SIZE=medium
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
WHISPER_WORKER_TOKEN=
WHISPER_ENABLE_DIARIZATION=false
PYANNOTE_AUTH_TOKEN=
```

Na API principal, configure:

```env
JURISFLOW_TRANSCRIPTION_PROVIDER=whisper_worker
JURISFLOW_WHISPER_WORKER_URL=https://seu-worker.up.railway.app
JURISFLOW_WHISPER_WORKER_TOKEN=<mesmo token do worker>
```

## Deploy Railway

Crie um segundo servico apontando para esta pasta. O `Dockerfile` instala
`ffmpeg`, `libsndfile1`, `faster-whisper` e dependencias de audio.

Start command:

```bash
pip install -r requirements.txt
gunicorn app:app --bind 0.0.0.0:$PORT --timeout 900
```

Se o Railway detectar o `Dockerfile`, nao precisa definir install command manual.

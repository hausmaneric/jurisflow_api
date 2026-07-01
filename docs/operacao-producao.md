# Operacao de producao

Este guia deixa a API, a consulta processual e a transcricao prontas para operar em ambientes separados.

## Servicos

1. API principal

- Pasta: `API`
- Start: `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 180`
- Healthcheck: `/api/v1/health`
- Banco: PostgreSQL do Railway em `JURISFLOW_DATABASE_URL`

2. Worker de transcricao

- Pasta: `API/transcription_worker`
- Dockerfile proprio
- Start: `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 900`
- Healthcheck: `/health`
- Readiness: `/ready`
- Variaveis minimas: `WHISPER_WORKER_TOKEN`, `WHISPER_MODEL_SIZE`, `WHISPER_DEVICE`, `WHISPER_COMPUTE_TYPE`

3. Conector server-side de tribunais

- Pasta: `API/server_court_connector`
- Dockerfile proprio
- Start: `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 900`
- Healthcheck: `/health`
- Variaveis minimas: `JURISFLOW_COURT_CONNECTOR_TOKEN`
- Para PJe real, configure `JURISFLOW_SERVER_PJE_MIDDLEWARE_URL` com o middleware contratado/autorizado.

4. Ponte local para A3

- Pasta: `API/local_court_bridge`
- Deve rodar na maquina onde o token USB/smartcard esta instalado.
- Start Windows: `powershell -ExecutionPolicy Bypass -File .\scripts\run_local_court_bridge.ps1`
- A chave privada do A3 nunca sobe para a nuvem.

5. Agente de certificado

- Pasta: `API/certificate_agent`
- Deve rodar junto da ponte local quando o advogado usar token fisico.
- Start Windows: `powershell -ExecutionPolicy Bypass -File .\scripts\run_certificate_agent.ps1`
- Variaveis minimas: `JURISFLOW_API_URL`, `CERTIFICATE_AGENT_TOKEN`, `JURISFLOW_LOCAL_BRIDGE_TOKEN`

## Railway

Crie tres servicos:

- `jurisflow-api`: raiz `API`.
- `jurisflow-transcription-worker`: raiz `API/transcription_worker`.
- `jurisflow-court-connector`: raiz `API/server_court_connector`.

Na API, configure:

- `JURISFLOW_TRANSCRIPTION_PROVIDER=whisper_worker`
- `JURISFLOW_WHISPER_WORKER_URL=https://URL-DO-WORKER`
- `JURISFLOW_WHISPER_WORKER_TOKEN=<mesmo token do worker>`
- `JURISFLOW_SERVER_COURT_CONNECTOR_URL=https://URL-DO-CONNECTOR/tribunal-sync`
- `JURISFLOW_SERVER_COURT_CONNECTOR_TOKEN=<mesmo token do connector>`
- `JURISFLOW_STORAGE_MODE=s3`

## Consulta processual

O fluxo correto e:

1. Consulta gratuita/publica no DataJud.
2. Se o usuario pedir aprofundamento, a API escolhe o tribunal pelo numero CNJ.
3. Para A1/cofre/cloud, usa o conector server-side.
4. Para A3 USB/smartcard, cria job para o agente local.

## Transcricao

O fluxo correto e:

1. Usuario sobe audio/video.
2. API gera URL assinada do arquivo.
3. API envia para o worker Whisper.
4. Worker devolve segmentos com horario e falante.
5. API salva segmentos, resumo, anotacoes e documento exportavel.

Para identificar nomes reais dos participantes, habilite diarizacao com `WHISPER_ENABLE_DIARIZATION=true` e configure `PYANNOTE_AUTH_TOKEN`. Sem diarizacao, o worker entrega `Falante 1`, `Falante 2` etc.

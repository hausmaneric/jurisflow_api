# Railway Checklist

## Runtime

- `Procfile`: `web: gunicorn app:app`
- `runtime.txt`: `python-3.12.8`
- dependencias em `requirements.txt`

## Banco

- criar PostgreSQL no Railway
- aplicar `database/schema.sql`
- usar `sslmode=require` em producao

## Configuracao

- preferir `JURISFLOW_DATABASE_URL`
- definir `JURISFLOW_SECRET_KEY`
- definir `JURISFLOW_SETUP_KEY`
- definir `JURISFLOW_DATAJUD_API_KEY` para consulta processual publica gratuita no CNJ/DataJud
- usar `JURISFLOW_DATAJUD_BASE_URL=https://api-publica.datajud.cnj.jus.br`
- a API publica do DataJud usa endpoints no formato `api_publica_<tribunal>/_search` e header `Authorization: APIKey <chave>`
- definir `JURISFLOW_TRANSCRIPTION_PROVIDER=manual` ou `whisper_worker`
- para transcricao automatica sem OpenAI: `JURISFLOW_WHISPER_WORKER_URL` e, se houver autenticacao, `JURISFLOW_WHISPER_WORKER_TOKEN`
- para consulta em tribunal com certificado, cadastrar A1 por arquivo seguro ou A3/token/provedor em `lawyer_certificates` e o conector real em `court_connectors`
- para A3/token USB/smartcard, configurar um agente local ou provedor no conector; a API nao recebe a chave privada nem exige arquivo do certificado
- evitar segredos reais em `_config.server.json`

## Verificacoes apos deploy

- `GET /api/v1/health`
- `GET /api/v1/ready`
- `GET /api/v1/routes`
- `POST /api/v1/setup/bootstrap`
- `POST /api/v1/auth/login`

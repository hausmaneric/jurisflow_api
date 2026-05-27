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
- evitar segredos reais em `_config.server.json`

## Verificacoes apos deploy

- `GET /api/v1/health`
- `GET /api/v1/ready`
- `GET /api/v1/routes`
- `POST /api/v1/setup/bootstrap`
- `POST /api/v1/auth/login`

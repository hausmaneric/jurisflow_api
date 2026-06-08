# JurisFlow API

API Flask preparada para deploy no Railway com PostgreSQL do proprio Railway.

## Base ativa

- `source/app.py`
- `source/controller/`
- `source/core/`
- `source/data/`
- `source/logic/`

O entrypoint raiz continua em `app.py`.

## Estrutura preservada

As pastas abaixo existem para manter o mesmo padrao estrutural do projeto de referencia:

- `classes/`
- `controller/`
- `models/`
- `database/`
- `docs/`
- `tests/`

## Endpoints iniciais

- `GET /api/v1/health`
- `GET /api/v1/ready`
- `GET /api/v1/routes`
- `GET /api/v1/conventions`
- `GET /api/v1/environment`
- `GET /api/v1/about`
- `POST /api/v1/public/signup`
- `POST /api/v1/setup/bootstrap`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/me`
- `GET|PUT /api/v1/company-settings`
- `POST /api/v1/auth/request-password-reset`
- `POST /api/v1/auth/reset-password`
- `GET|POST /api/v1/clients`
- `GET|POST /api/v1/lawyers`
- `GET|POST /api/v1/cases`
- `GET|POST /api/v1/appointments`
- `GET|POST /api/v1/documents`
- `GET|POST /api/v1/document-templates`
- `POST /api/v1/documents/generate`
- `GET|POST /api/v1/message-templates`
- `GET|POST /api/v1/messages`
- `POST /api/v1/messages/send-template`
- `GET|POST /api/v1/tasks`
- `GET|POST /api/v1/notifications`
- `GET /api/v1/audit`
- `GET /api/v1/reports/timeline`

## Deploy no Railway

- `Procfile`: `web: gunicorn app:app`
- `runtime.txt`: `python-3.12.8`
- `railway.json`: healthcheck e comando de start
- `.env.example`: variaveis recomendadas

Em producao, prefira `JURISFLOW_DATABASE_URL` fornecida pelo PostgreSQL do Railway.

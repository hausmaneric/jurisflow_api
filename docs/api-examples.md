# API Examples

## Bootstrap inicial

`POST /api/v1/setup/bootstrap`

Headers:

- `X-Setup-Key: <JURISFLOW_SETUP_KEY>`

Body:

```json
{
  "company_code": "demo-legal",
  "company_name": "Demo Legal",
  "company_email": "contato@demolegal.com",
  "admin_name": "Admin Demo",
  "admin_email": "admin@demolegal.com",
  "admin_password": "123456",
  "timezone": "America/Sao_Paulo",
  "locale": "pt-BR"
}
```

## Cadastro publico de escritorio

`POST /api/v1/public/signup`

```json
{
  "company_code": "demo-legal",
  "company_name": "Demo Legal",
  "company_email": "contato@demolegal.com",
  "company_phone": "11999999999",
  "admin_name": "Admin Demo",
  "admin_email": "admin@demolegal.com",
  "admin_phone": "11988888888",
  "admin_password": "Senha@123",
  "timezone": "America/Sao_Paulo",
  "locale": "pt-BR"
}
```

## Login

`POST /api/v1/auth/login`

```json
{
  "company_code": "demo-legal",
  "email": "admin@demolegal.com",
  "password": "123456"
}
```

## Criar cliente

`POST /api/v1/clients`

Headers:

- `Authorization: Bearer <access_token>`

```json
{
  "name": "Cliente Exemplo",
  "document": "12345678900",
  "email": "cliente@exemplo.com",
  "phone": "11999999999",
  "status": "active"
}
```

## Gerar documento por template

`POST /api/v1/documents/generate`

```json
{
  "template_id": "uuid-do-template",
  "context": {
    "client": {
      "name": "Cliente Exemplo"
    },
    "company": {
      "name": "Demo Legal"
    }
  }
}
```

## Enviar mensagem por template

`POST /api/v1/messages/send-template`

```json
{
  "template_id": "uuid-do-template",
  "recipient": "5511999999999",
  "channel": "whatsapp",
  "context": {
    "client": {
      "name": "Cliente Exemplo"
    }
  }
}
```

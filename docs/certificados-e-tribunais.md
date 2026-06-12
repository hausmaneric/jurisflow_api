# Certificados digitais e consulta em tribunais

O JurisFlow suporta dois cenarios de certificado digital para consulta autenticada em tribunais.

## A1 por arquivo

Use quando o escritorio possui um arquivo `.pfx`/`.p12` armazenado em cofre ou storage seguro.

Campos principais em `lawyer_certificates`:

- `certificate_type=A1`
- `certificate_access_mode=file_a1`
- `certificate_file_url=<url segura ou referencia interna>`
- `certificate_password_secret=<referencia do segredo, nunca senha em texto aberto>`

O conector recebe `certificate.file_url` e deve buscar o arquivo no cofre autorizado.

O A1 pode funcionar de duas formas:

- `server_sync_endpoint`: conector remoto seguro acessado pela API no Railway.
- `local_sync_endpoint`: agente local executa a consulta no computador autorizado, util quando o acesso ao tribunal depender de ambiente local, VPN, driver, navegador ou middleware instalado.

## A3 token USB/smartcard

Use quando o certificado esta em dispositivo fisico do advogado ou escritorio.
A chave privada nao sai do token, portanto o JurisFlow nao exige arquivo.

Campos principais:

- `certificate_type=A3`
- `certificate_access_mode=token_a3_local`
- `device_identifier=<serial/apelido do token>`
- `local_agent_id=<id da maquina/agente que tem acesso ao token>`

Nesse modo, a consulta deve passar pelo agente local ou ponte segura instalada na maquina onde o token esta conectado. O agente faz a assinatura/autenticacao localmente e devolve apenas o resultado autorizado.

## Cadastro automatico de conectores

Para cadastrar os conectores padrao de todos os tribunais DataJud no escritorio atual:

```http
POST /api/v1/court-connectors/seed-defaults
Authorization: Bearer <token_admin>
Content-Type: application/json

{
  "sync_endpoint": "http://127.0.0.1:8765/tribunal-sync"
}
```

O endpoint e idempotente: se o conector ja existir para o `court_code`, ele atualiza; se nao existir, cria.

Esses conectores ficam prontos para A1 e A3:

- Para A1, usam preferencialmente `JURISFLOW_SERVER_COURT_CONNECTOR_URL`, quando configurado.
- Para certificado em nuvem, usam preferencialmente `JURISFLOW_SERVER_COURT_CONNECTOR_URL`, quando configurado.
- Para A3/token USB, usam obrigatoriamente a ponte local, pois o token/pen drive precisa estar conectado ao computador autorizado.

Para operar sem depender do cliente, configure o conector remoto:

```text
JURISFLOW_SERVER_COURT_CONNECTOR_URL=https://seu-conector/tribunal-sync
JURISFLOW_SERVER_COURT_CONNECTOR_TOKEN=<token forte>
```

Depois execute novamente `POST /api/v1/court-connectors/seed-defaults`. O seed passa a registrar os tribunais em modo server-first.

O contrato da ponte local deve receber `case_number`, `court_system` e dados do certificado autorizado, e responder:

```json
{
  "documents": [],
  "movements": []
}
```

Para ponte local, use o valor padrao `http://127.0.0.1:8765/tribunal-sync`, porque quem chama esse endereco e o agente local, nao o Railway.

A implementacao local pronta esta em `local_court_bridge/`. Ela deve ser executada no mesmo computador do certificado ou no ambiente autorizado pelo escritorio. Use `JURISFLOW_LOCAL_BRIDGE_TOKEN` para proteger a ponte local e informe o mesmo valor no `certificate_agent`.

### Fluxo com agente local A1 ou A3

1. Um administrador registra o agente local:

```http
POST /api/v1/certificate-agents/register
Authorization: Bearer <token_usuario>
```

Exemplo:

```json
{
  "name": "Agente escritorio SP",
  "agent_key": "escritorio-sp-01"
}
```

A resposta traz `agent_token` uma unica vez. Esse token fica instalado no agente local.

2. O certificado do advogado usa A1 ou A3.

A1 por arquivo com agente local:

```json
{
  "certificate_type": "A1",
  "certificate_access_mode": "file_a1",
  "certificate_file_url": "storage://cofre/certificado.pfx",
  "local_agent_id": "escritorio-sp-01"
}
```

A3 por token USB/smartcard:

```json
{
  "certificate_type": "A3",
  "certificate_access_mode": "token_a3_local",
  "device_identifier": "token-oab-joao",
  "local_agent_id": "escritorio-sp-01"
}
```

3. Ao consultar tribunal por ponte local, a API cria um job pendente em `certificate_agent_jobs`.

4. O agente local busca o job:

```http
GET /api/v1/certificate-agents/jobs/next
Authorization: Bearer <agent_token>
```

5. O agente executa a consulta no ambiente local onde o A1 esta acessivel ou onde o token USB/smartcard A3 esta conectado.

Na maquina local, execute dois processos:

```powershell
cd C:\developer.workspace\Projetos\JurisFlow\API\local_court_bridge
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
$env:JURISFLOW_LOCAL_BRIDGE_TOKEN="token-local-forte"
python app.py
```

```powershell
cd C:\developer.workspace\Projetos\JurisFlow\API\certificate_agent
$env:JURISFLOW_API_URL="https://web-production-3c57a.up.railway.app/api/v1"
$env:CERTIFICATE_AGENT_TOKEN="<agent_token>"
$env:JURISFLOW_LOCAL_BRIDGE_TOKEN="token-local-forte"
python agent.py
```

Drivers especificos de tribunal ficam em `local_court_bridge/drivers`. O driver `pje.py` repassa para uma automacao local configurada em `JURISFLOW_PJE_AUTOMATION_URL`, mantendo certificado, PIN e sessao do tribunal fora do Railway.

6. O agente devolve o resultado:

```http
POST /api/v1/certificate-agents/jobs/{job_id}/complete
Authorization: Bearer <agent_token>
```

Corpo esperado:

```json
{
  "documents": [],
  "movements": []
}
```

Se houver erro:

```json
{
  "error": "Descricao do erro no tribunal ou no token"
}
```

## Certificado em nuvem/provedor

Use quando a assinatura/autenticacao ocorre via provedor externo.

Campos principais:

- `certificate_type=A3`
- `certificate_access_mode=cloud_provider`
- `certificate_provider=<nome do provedor>`
- `cloud_certificate_ref=<referencia do certificado no provedor>`

O conector deve usar a API do provedor configurado.

## Payload enviado ao conector

Na consulta autenticada do tribunal, a API envia:

```json
{
  "case_number": "00000000000000000000",
  "case_id": "...",
  "court_system": "pje",
  "certificate": {
    "id": "...",
    "type": "A3",
  "access_mode": "file_a1 ou token_a3_local",
    "provider": "local_agent",
    "file_url": "",
    "device_identifier": "token-oab-joao",
    "local_agent_id": "escritorio-sp-01",
    "cloud_certificate_ref": "",
    "metadata": {}
  }
}
```

## Regras

- A1 sem `certificate_file_url` fica com status `invalid_config`.
- A1 pode usar agente local quando o conector exigir ponte local.
- A3/token pode ser validado sem arquivo, desde que tenha agente/dispositivo informado, consentimento aceito e nao esteja vencido.
- Certificado em nuvem exige `certificate_provider` e `cloud_certificate_ref`.
- Toda consulta autenticada registra auditoria de uso do certificado.

# JurisFlow Certificate Agent

Agente local para consultas de tribunal que dependem de certificado A3 em token USB/smartcard.

Ele roda na maquina que tem acesso ao token fisico, busca jobs pendentes na API do JurisFlow e chama o conector configurado no job. O conector pode ser um middleware local, uma ponte de tribunal ou um servico interno que consiga usar o certificado A3 do computador.

## Variaveis

```env
JURISFLOW_API_URL=https://web-production-3c57a.up.railway.app/api/v1
CERTIFICATE_AGENT_TOKEN=<token gerado em /certificate-agents/register>
CERTIFICATE_AGENT_INTERVAL_SECONDS=10
```

## Execucao

```bash
pip install -r requirements.txt
python agent.py
```

## Contrato

O job recebido possui:

```json
{
  "request_payload": {
    "endpoint": "https://endpoint-do-conector",
    "headers": {},
    "body": {}
  }
}
```

O endpoint do conector deve responder JSON com:

```json
{
  "documents": [],
  "movements": []
}
```

Se houver erro de token, PIN, tribunal ou certificado, o agente devolve o erro para a API e o job fica marcado como `failed`.

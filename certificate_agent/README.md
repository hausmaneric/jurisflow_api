# JurisFlow Certificate Agent

Agente local para consultas de tribunal que dependem de certificado A3 em token USB/smartcard, certificado instalado no Windows ou provedor local.

Ele roda na maquina que tem acesso ao certificado fisico/instalado, busca jobs pendentes na API do JurisFlow e chama o conector configurado no job. O certificado, a chave privada e o PIN nunca sao enviados para a API, para o Railway ou para o banco.

O conector pode ser:

- um middleware local que usa o certificado do Windows/token;
- uma ponte de tribunal instalada no computador do advogado;
- um servico interno que automatiza o acesso ao tribunal com certificado local.

O JurisFlow recebe apenas o resultado autorizado da consulta: andamentos, metadados e documentos permitidos.

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

No Windows, apos registrar o agente na tela de Advogados > Certificado digital, use o comando exibido pela plataforma ou configure as variaveis no PowerShell/CMD antes de iniciar.

## Fluxo sem upload de certificado

1. Cadastre o advogado.
2. Em certificado, escolha `A3 token USB/smartcard`.
3. Informe `Identificacao do token` e `ID do agente local`.
4. Clique em `Registrar agente local`.
5. Copie o token exibido uma unica vez.
6. Execute este agente no computador onde o certificado esta conectado.
7. Cadastre o conector do tribunal com o endpoint/middleware que acessa o tribunal localmente.
8. No processo, use `Consultar tribunal com certificado`.

Este fluxo evita envio de arquivo `.pfx/.p12`, PIN ou chave privada.

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

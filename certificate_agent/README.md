# JurisFlow Certificate Agent

Agente local para consultas de tribunal que dependem de certificado A1 por arquivo, certificado A3 em token USB/smartcard, certificado instalado no Windows ou provedor local.

Ele roda na maquina que tem acesso ao certificado fisico/instalado ou ao arquivo A1 autorizado, busca jobs pendentes na API do JurisFlow e chama o conector configurado no job. A chave privada e o PIN nunca sao enviados para a API, para o Railway ou para o banco.

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

## Fluxo para A1 por arquivo

1. Cadastre o advogado.
2. Em certificado, escolha `A1 por arquivo seguro`.
3. Informe a URL/referencia segura do arquivo A1.
4. Se o tribunal usar ponte local, informe `ID do agente local`.
5. Clique em `Registrar agente local` se ainda nao existir agente para essa maquina.
6. Execute este agente no computador autorizado.
7. Cadastre ou atualize o conector do tribunal com `requires_local_agent=true` para ponte local ou `server_sync_endpoint` para conector remoto seguro.

## Fluxo sem upload para A3/token

1. Cadastre o advogado.
2. Em certificado, escolha `A3 token USB/smartcard`.
3. Informe `Identificacao do token` e `ID do agente local`.
4. Clique em `Registrar agente local`.
5. Copie o token exibido uma unica vez.
6. Execute este agente no computador onde o certificado esta conectado.
7. Cadastre o conector do tribunal com o endpoint/middleware que acessa o tribunal localmente.
8. No processo, use `Consultar tribunal com certificado`.

Este fluxo evita envio de PIN ou chave privada. No A3, tambem evita envio de arquivo, porque o certificado permanece no token/pen drive.

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

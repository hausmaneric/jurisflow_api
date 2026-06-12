# JurisFlow Server Court Connector

Conector remoto para consultas autenticadas sem depender do computador do cliente.
Use este servico para:

- certificado A1 armazenado em cofre/storage seguro;
- certificado em nuvem/provedor;
- middleware contratado de PJe, e-SAJ, eproc ou Projudi.

Ele nao suporta A3 USB/token fisico, porque o dispositivo precisa estar conectado
ao computador onde a chave privada esta protegida.

## Variaveis

```text
JURISFLOW_SERVER_COURT_CONNECTOR_TOKEN=<token forte>
JURISFLOW_SERVER_PJE_MIDDLEWARE_URL=<url do middleware PJe>
JURISFLOW_SERVER_PJE_MIDDLEWARE_TOKEN=<token do middleware>
```

Na API principal, configure:

```text
JURISFLOW_SERVER_COURT_CONNECTOR_URL=https://seu-conector/tribunal-sync
JURISFLOW_SERVER_COURT_CONNECTOR_TOKEN=<mesmo token>
```

Depois rode `POST /api/v1/court-connectors/seed-defaults`. Os conectores passam
a usar o modo server-first para A1 e certificado em nuvem.

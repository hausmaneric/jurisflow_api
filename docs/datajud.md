# DataJud CNJ

Referencia oficial: https://datajud-wiki.cnj.jus.br/api-publica/

## Configuracao

```env
JURISFLOW_DATAJUD_API_KEY=<chave oficial CNJ>
JURISFLOW_DATAJUD_BASE_URL=https://api-publica.datajud.cnj.jus.br
```

## Padrao usado

O JurisFlow chama:

```text
POST https://api-publica.datajud.cnj.jus.br/api_publica_<tribunal>/_search
Authorization: APIKey <chave>
Content-Type: application/json
```

Exemplo de corpo:

```json
{
  "query": {
    "match": {
      "numeroProcesso": "00000000000000000000"
    }
  },
  "size": 10
}
```

## Fluxo no JurisFlow

1. O sistema identifica o tribunal pelo numero CNJ ou pelo campo do processo.
2. Consulta o DataJud publico.
3. Atualiza tribunal, vara/fase e andamentos retornados.
4. Registra log em `case_sync_logs`.
5. Se solicitado `sync-full`, tenta em seguida o conector do tribunal com certificado A1.

## Observacoes

- A chave DataJud nao pode ser gerada pelo JurisFlow; ela deve ser emitida/autorizada no ambiente oficial do CNJ.
- O DataJud publico nao substitui autos integrais do tribunal. Para documentos e movimentos restritos, use conector de tribunal com certificado.

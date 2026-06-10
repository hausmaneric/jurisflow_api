# DataJud CNJ

Referencias oficiais:

- https://datajud-wiki.cnj.jus.br/api-publica/acesso/
- https://datajud-wiki.cnj.jus.br/api-publica/endpoints/
- https://datajud-wiki.cnj.jus.br/api-publica/exemplos/exemplo1/
- https://datajud-wiki.cnj.jus.br/api-publica/exemplos/exemplo2/
- https://datajud-wiki.cnj.jus.br/api-publica/exemplos/exemplo3/

## Configuracao

```env
JURISFLOW_DATAJUD_API_KEY=<chave publica vigente da Wiki CNJ>
JURISFLOW_DATAJUD_BASE_URL=https://api-publica.datajud.cnj.jus.br
```

Em 10/06/2026, a chave publica informada na Wiki oficial e:

```text
cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw==
```

A aplicacao usa essa chave como fallback, mas a variavel `JURISFLOW_DATAJUD_API_KEY` deve ser mantida no Railway para trocar rapidamente se o CNJ alterar a chave.

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

Tambem e possivel usar Query DSL completa, como nos exemplos oficiais:

```json
{
  "court": "tjdft",
  "size": 100,
  "query_dsl": {
    "query": {
      "bool": {
        "must": [
          { "match": { "classe.codigo": 1116 } },
          { "match": { "orgaoJulgador.codigo": 13597 } }
        ]
      }
    },
    "sort": [
      { "@timestamp": { "order": "asc" } }
    ]
  }
}
```

Para proxima pagina, envie o `next_search_after` retornado:

```json
{
  "court": "tjdft",
  "size": 100,
  "search_after": [1681366085550],
  "query_dsl": {
    "query": {
      "bool": {
        "must": [
          { "match": { "classe.codigo": 1116 } },
          { "match": { "orgaoJulgador.codigo": 13597 } }
        ]
      }
    },
    "sort": [
      { "@timestamp": { "order": "asc" } }
    ]
  }
}
```

## Endpoints JurisFlow

```text
GET /api/v1/datajud/courts
POST /api/v1/datajud/search
POST /api/v1/cases/<case_id>/sync-datajud
POST /api/v1/cases/<case_id>/sync-full
```

`POST /api/v1/datajud/search` aceita:

- `court`, `tribunal`, `datajud_court` ou `court_code`: alias oficial, exemplo `tjsp`, `tjdft`, `trf3`, `trt2`.
- `case_number` ou `numeroProcesso`: numero CNJ com 20 digitos.
- `query_dsl`, `dsl` ou `body`: corpo Elasticsearch conforme exemplos oficiais.
- `size`: de 1 a 10000.
- `sort` e `search_after`: paginacao eficiente conforme Wiki DataJud.

## Fluxo no JurisFlow

1. O sistema identifica o tribunal pelo numero CNJ ou pelo campo do processo.
2. Consulta o DataJud publico.
3. Atualiza tribunal, vara/fase e andamentos retornados.
4. Registra log em `case_sync_logs`.
5. Se solicitado `sync-full`, tenta em seguida o conector do tribunal com certificado A1.

## Observacoes

- A chave publica DataJud e informada na Wiki oficial e pode ser alterada pelo CNJ.
- O DataJud publico nao substitui autos integrais do tribunal. Para documentos e movimentos restritos, use conector de tribunal com certificado.

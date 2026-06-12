# JurisFlow Local Court Bridge

Este servico roda no computador autorizado, onde o certificado A1/A3 esta disponivel.
Ele recebe jobs do `certificate_agent`, chama o driver local do tribunal e devolve
documentos/movimentos padronizados para a API.

## Executar

```powershell
cd C:\developer.workspace\Projetos\JurisFlow\API\local_court_bridge
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
$env:JURISFLOW_LOCAL_BRIDGE_TOKEN="troque-este-token"
python app.py
```

O endpoint local padrao fica em:

```text
http://127.0.0.1:8765/tribunal-sync
```

## Contrato de resposta

```json
{
  "documents": [
    {
      "title": "Peticao inicial",
      "file_url": "file:///C:/jurisflow/documentos/peticao.pdf",
      "file_type": "pdf",
      "external_id": "123"
    }
  ],
  "movements": [
    {
      "code": "123",
      "movement_date": "2026-06-12",
      "title": "Juntada de documento",
      "description": "Documento juntado aos autos."
    }
  ]
}
```

## Drivers

Drivers ficam em `drivers/` e devem expor `CourtDriver.sync_case(payload)`.
O driver `pje.py` repassa para uma automacao local configurada em
`JURISFLOW_PJE_AUTOMATION_URL`. Isso evita armazenar PIN, chave privada ou
certificado A3 no Railway.

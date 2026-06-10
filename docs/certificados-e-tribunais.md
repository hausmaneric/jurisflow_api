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

## A3 token USB/smartcard

Use quando o certificado esta em dispositivo fisico do advogado ou escritorio.
A chave privada nao sai do token, portanto o JurisFlow nao exige arquivo.

Campos principais:

- `certificate_type=A3`
- `certificate_access_mode=token_a3_local`
- `device_identifier=<serial/apelido do token>`
- `local_agent_id=<id da maquina/agente que tem acesso ao token>`

Nesse modo, o conector do tribunal deve chamar um agente local ou ponte segura instalada na maquina onde o token esta conectado. O agente faz a assinatura/autenticacao localmente e devolve apenas o resultado autorizado.

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
    "access_mode": "token_a3_local",
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
- A3/token pode ser validado sem arquivo, desde que tenha consentimento aceito e nao esteja vencido.
- Certificado em nuvem exige `certificate_provider` e `cloud_certificate_ref`.
- Toda consulta autenticada registra auditoria de uso do certificado.

# Storage seguro

O JurisFlow suporta dois modos:

- `local`: apenas desenvolvimento/local.
- `s3`: producao com bucket privado S3 compativel, como Cloudflare R2, AWS S3, MinIO ou Backblaze B2.

## Variaveis

```env
JURISFLOW_STORAGE_MODE=s3
JURISFLOW_S3_ENDPOINT_URL=https://<account>.r2.cloudflarestorage.com
JURISFLOW_S3_REGION=auto
JURISFLOW_S3_BUCKET=jurisflow-private
JURISFLOW_S3_ACCESS_KEY_ID=<access-key>
JURISFLOW_S3_SECRET_ACCESS_KEY=<secret-key>
JURISFLOW_S3_PRESIGN_EXPIRES_SECONDS=3600
```

Se `JURISFLOW_STORAGE_PUBLIC_BASE_URL` ficar vazio, a API retorna URLs internas
`/api/v1/uploads/...` que redirecionam para URL assinada. Isso permite que o
worker de transcricao baixe audio/video sem tornar o bucket publico.

## Certificados A1

Para A1 server-side, armazene o `.pfx/.p12` no cofre/storage privado e grave em
`lawyer_certificates.certificate_file_url` uma URL segura ou referencia interna.
Nunca versionar senha, certificado, PIN ou chave privada.

## Transcricao

O fluxo recomendado e:

1. Web envia audio/video em `POST /api/v1/documents/upload`.
2. API salva no storage seguro.
3. Transcricao aponta para `file_url`.
4. Worker baixa por URL assinada e processa com Whisper/Pyannote.

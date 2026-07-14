# Gmail Cloud Run Downloader v1

Incluye Gmail API, Drive API, adjuntos, enlaces directos, enlaces compartidos de Drive, SendGB con Playwright, filtros y etiquetado de correos.

## APIs
Habilita Gmail API, Google Drive API, Cloud Run, Cloud Build, Artifact Registry, Secret Manager y Cloud Scheduler.

## OAuth
1. Configura pantalla OAuth y agrega tu cuenta como usuario de prueba.
2. Crea credenciales OAuth tipo Desktop App y descarga `credentials.json`.
3. En un PC con Python ejecuta:
   `pip install -r requirements.txt`
   `python oauth_bootstrap.py`
4. Se genera `token.json`.
5. No subas esos archivos a GitHub.

## Secret Manager
Crea:
- `google-client-secret-json` con el contenido completo de credentials.json
- `google-oauth-token-json` con el contenido completo de token.json

## Artifact Registry
Crea repositorio Docker `gmail-downloader` en `southamerica-west1`.

## Cloud Build
Vincula GitHub, usa `cloudbuild.yaml` y estas sustituciones:
- `_REGION=southamerica-west1`
- `_REPOSITORY=gmail-downloader`
- `_IMAGE=gmail-cloud-run`

## Cloud Run Job
Variables:
- `GMAIL_QUERY=is:unread`
- `PROCESSED_LABEL=Descarga-Automatica-Procesado`
- `MAX_EMAILS=20`
- `DRIVE_FOLDER_ID=ID_DE_LA_CARPETA`
- `DOWNLOAD_DIR=/tmp/descargas`
- `ENABLE_SENDGB=true`
- `MARK_AS_READ=true`

Filtros opcionales:
- `ONLY_FROM=persona@empresa.cl`
- `ONLY_FROM_DOMAIN=@inser.cl`
- `KEYWORD=orden de compra`
- `ALLOWED_EXTENSIONS=.pdf,.xlsx,.xls,.xml,.zip,.doc,.docx,.csv`

Secretos como variables:
- `GOOGLE_CLIENT_SECRET_JSON` -> `google-client-secret-json:latest`
- `GOOGLE_OAUTH_TOKEN_JSON` -> `google-oauth-token-json:latest`

Configuración sugerida: 1 CPU, 2 GiB, timeout 30 min, 1 reintento, 1 tarea.

## Scheduler
Programa el Job, por ejemplo cada 30 minutos: `*/30 * * * *`, zona `America/Santiago`.

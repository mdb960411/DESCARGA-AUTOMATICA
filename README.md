# Gmail Cloud Run Downloader V3

Aplicación modular para procesar correos de Gmail, descargar adjuntos y enlaces, y subir los archivos obtenidos a Google Drive.

## Proveedores soportados

- Descarga directa por HTTP/HTTPS
- Google Drive
- WeTransfer
- TransferNow
- SendAllFiles
- SendGB

## Arquitectura

La lógica de descarga está separada dentro de `app/downloaders/`:

- `manager.py`: detecta el proveedor y dirige la descarga.
- `direct.py`: archivos directos por HTTP/HTTPS.
- `drive.py`: enlaces compartidos de Google Drive.
- `browser.py`: automatización común con Playwright.
- `providers.py`: configuración específica de cada proveedor.
- `smart_browser.py`: búsqueda adicional de botones de descarga.
- `filters.py`: bloqueo de enlaces decorativos o de seguimiento.

`app/downloaders_legacy.py` ya no es utilizado por la aplicación.

## Variables de Cloud Run Job

- `GMAIL_QUERY=is:unread`
- `PROCESSED_LABEL=Descarga-Automatica-Procesado`
- `MAX_EMAILS=20`
- `DRIVE_FOLDER_ID=ID_DE_LA_CARPETA`
- `DOWNLOAD_DIR=/tmp/descargas`
- `ENABLE_SENDGB=true`
- `MARK_AS_READ=true`

Filtros opcionales:

- `ONLY_FROM=persona@empresa.cl`
- `ONLY_FROM_DOMAIN=@empresa.cl`
- `KEYWORD=orden de compra`
- `ALLOWED_EXTENSIONS=.pdf,.xlsx,.xls,.xml,.zip,.doc,.docx,.csv`

Secretos:

- `GOOGLE_CLIENT_SECRET_JSON`
- `GOOGLE_OAUTH_TOKEN_JSON`

No subas `token.json`, `credentials.json`, `.env` ni otros archivos sensibles al repositorio.

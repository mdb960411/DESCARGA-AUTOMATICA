# Descarga Automática Gmail → Google Drive V4.1

Job de Cloud Run para procesar correos de Gmail, descargar adjuntos y enlaces
de transferencia, y guardar los archivos obtenidos en Google Drive.

Esta versión está preparada para trabajos de industria gráfica y archivos
grandes como `.ai`, `.ps`, `.eps`, `.indd`, `.psd`, `.tif`, `.pdf` y paquetes
comprimidos.

## Cambios principales de V4.1

- Usa un volumen de Cloud Storage para no guardar archivos grandes en la
  memoria de Cloud Run.
- Cuando es posible, Playwright captura el enlace real y cierra Chromium antes
  de continuar la descarga por HTTP en bloques.
- Las subidas a Drive son reanudables y usan fragmentos pequeños.
- Evita duplicados en Drive cuando un correo debe reintentarse.
- No marca un correo como procesado si una descarga o subida falla.
- Crea etiquetas de Gmail para estados procesado, parcial y error.
- Excluye automáticamente los correos con error para evitar ciclos infinitos.
- Oculta los tokens completos de los enlaces en Cloud Logging.
- Elimina los archivos temporales inmediatamente después de cada correo.
- Espera la carga dinámica y la validación de seguridad de SendAllFiles.
- Descarga todos los archivos de una misma transferencia de SendAllFiles.
- Distingue enlaces caducados de fallos técnicos cuando el proveedor lo indica.
- Evita probar repetidamente variantes del mismo enlace de WeTransfer.
- Etiqueta como ignorados los correos sin archivos, sin marcarlos como error ni
  como leídos.
- Cierra Playwright antes de detener su canal y elimina el ruido
  `CancelledError`/`TargetClosedError`.

## Proveedores soportados

- Adjuntos de Gmail
- Descarga directa por HTTP/HTTPS
- Google Drive
- WeTransfer
- TransferNow
- SendAllFiles
- SendGB
- SwissTransfer

## Flujo

1. Busca correos que cumplan la consulta configurada.
2. Extrae adjuntos y enlaces válidos.
3. Descarga en `/mnt/descargas`, montado sobre Cloud Storage.
4. Sube cada archivo a Google Drive de forma reanudable.
5. Etiqueta el correo según el resultado.
6. Elimina la copia temporal.

## Variables obligatorias

- `GOOGLE_CLIENT_SECRET_JSON`
- `GOOGLE_OAUTH_TOKEN_JSON`
- `DRIVE_FOLDER_ID`
- `DOWNLOAD_DIR=/mnt/descargas`

## Variables recomendadas

```text
GMAIL_QUERY=is:unread
PROCESSED_LABEL=Descarga-Automatica-Procesado
ERROR_LABEL=Descarga-Automatica-Error
PARTIAL_LABEL=Descarga-Automatica-Parcial
IGNORED_LABEL=Descarga-Automatica-Ignorado
MAX_EMAILS=20
MAX_FILE_SIZE_MB=8192
DOWNLOAD_CHUNK_SIZE_MB=4
UPLOAD_CHUNK_SIZE_MB=8
UPLOAD_RETRIES=3
DOWNLOAD_TIMEOUT_SECONDS=1800
BROWSER_HTTP_HANDOFF=true
EXCLUDE_ERROR_MESSAGES=true
EXCLUDE_IGNORED_MESSAGES=true
ENABLE_SENDGB=true
MARK_AS_READ=true
```

Filtros opcionales:

```text
ONLY_FROM=persona@empresa.cl
ONLY_FROM_DOMAIN=@empresa.cl
KEYWORD=orden de compra
```

## Extensiones

Si `ALLOWED_EXTENSIONS` no está definida, se utiliza una lista segura orientada
a producción gráfica. Para configurarla manualmente:

```text
.ai,.ait,.ps,.eps,.pdf,.zip,.rar,.7z,.indd,.idml,.psd,.psb,.tif,.tiff,.jpg,.jpeg,.png,.svg,.cdr,.afdesign,.afphoto,.xlsx,.xls,.xml,.csv,.doc,.docx
```

## Estados de Gmail

- `Descarga-Automatica-Procesado`: todos los archivos terminaron correctamente.
- `Descarga-Automatica-Parcial`: algunos archivos terminaron y otros fallaron.
- `Descarga-Automatica-Error`: el mensaje requiere revisión.
- `Descarga-Automatica-Ignorado`: el correo no contenía archivos útiles o no
  cumplía las reglas. Se conserva como no leído.

Los mensajes con etiquetas de error o ignorado se excluyen de ejecuciones
posteriores. Para reintentar un error, corrige la causa, elimina la etiqueta
`Descarga-Automatica-Error` y conserva el mensaje como no leído.

## Despliegue

Consulta [DESPLIEGUE_PASO_A_PASO.md](DESPLIEGUE_PASO_A_PASO.md).

## Seguridad

No subas `token.json`, `credentials.json`, `.env` ni secretos al repositorio.
El bucket temporal debe permanecer privado y la cuenta del job solo debe tener
el rol `roles/storage.objectUser` sobre ese bucket.

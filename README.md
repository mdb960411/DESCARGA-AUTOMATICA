# Descarga Automática Gmail → Google Drive V4.5.1

Job de Cloud Run para procesar correos de Gmail, descargar adjuntos y enlaces
de transferencia, y guardar los archivos obtenidos en Google Drive.

Esta versión está preparada para trabajos de industria gráfica y archivos
grandes como `.ai`, `.ps`, `.eps`, `.indd`, `.psd`, `.tif`, `.pdf` y paquetes
comprimidos.

## Cambios principales de V4.5.1

- Espera hasta 45 segundos el botón real de WeTransfer.
- Descarta enlaces publicitarios como `Sé Ultimate`, planes y promociones,
  aunque su URL contenga la palabra `download`.
- Reintenta WeTransfer hasta tres veces con un navegador limpio cuando la
  interfaz falla de forma transitoria.
- Reintenta el correo en ejecuciones posteriores antes de declararlo como
  error definitivo.
- Reconoce duplicados por mensaje, transferencia y contenido.
- Verifica que Gmail haya aplicado efectivamente cada etiqueta de estado.
- Ignora confirmaciones de envío de TransferNow.
- Evita ejecuciones superpuestas cuando Cloud Scheduler activa el job cada
  15 minutos.

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
- SendAllFiles usa un perfil de navegador compatible con su aplicación
  dinámica: User-Agent nativo y Service Workers habilitados.
- Busca controles de descarga tanto en la página principal como en marcos
  internos.
- Conserva la sesión validada de SendAllFiles y descarga mediante Chromium
  directamente sobre el volumen externo.
- Registra un diagnóstico seguro si la interfaz no aparece, sin publicar
  enlaces, tokens ni nombres de archivos.
- Cuando Cloudflare no termina la validación de SendAllFiles, etiqueta el
  correo como `Descarga-Automatica-Manual` en vez de confundirlo con un enlace
  caducado.
- WeTransfer, TransferNow y SwissTransfer usan el User-Agent nativo de
  Chromium, buscan controles dentro de marcos y soportan interfaces de varios
  pasos.
- El navegador reconoce botones por texto, accesibilidad, `data-testid`,
  título y destino, y puede continuar la búsqueda después de un primer clic.
- Si una descarga no genera el evento habitual de Chromium, puede recuperar
  una respuesta de archivo detectada en la red y continuar por HTTP en bloques.
  La respuesta debe tener evidencia fuerte de ser el archivo real.
- No extrae imágenes, logos ni píxeles incrustados directamente desde el HTML
  del correo.
- Bloquea respuestas web de analítica, cookies, publicidad e interfaces, aunque
  su URL contenga la palabra `download`.
- WeTransfer acepta su etapa de condiciones y conserva en Chromium las URLs de
  descarga de un solo uso.
- Si un correo de WeTransfer contiene variantes del mismo enlace, una variante
  correcta descarta los fallos previos de sus alternativas.
- TransferNow puede continuar la búsqueda cuando el primer control abre otra
  pestaña o una segunda etapa.
- Descarta candidatos publicitarios y elementos no interactivos del navegador
  inteligente.
- En caso de fallo registra descripciones seguras de los controles visibles,
  sin exponer los enlaces privados.
- El resumen final distingue `OK`, `REQUIERE_ATENCION_MANUAL` y
  `COMPLETADO_CON_ERRORES`.

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
MANUAL_LABEL=Descarga-Automatica-Manual
RETRY_LABEL=Descarga-Automatica-Reintento
MAX_EMAILS=20
MAX_FILE_SIZE_MB=8192
DOWNLOAD_CHUNK_SIZE_MB=4
UPLOAD_CHUNK_SIZE_MB=8
UPLOAD_RETRIES=3
DOWNLOAD_TIMEOUT_SECONDS=1800
BROWSER_HTTP_HANDOFF=true
EXCLUDE_ERROR_MESSAGES=true
EXCLUDE_IGNORED_MESSAGES=true
EXCLUDE_MANUAL_MESSAGES=true
BROWSER_ACTION_DIAGNOSTICS=true
ENABLE_SENDGB=true
MARK_AS_READ=true
WETRANSFER_DOWNLOAD_ATTEMPTS=3
PROVIDER_RETRY_DELAY_SECONDS=2
TRANSIENT_RETRY_RUNS=3
EXECUTION_LOCK_TTL_SECONDS=3600
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
- `Descarga-Automatica-Manual`: el enlace sigue requiriendo intervención
  humana, por ejemplo cuando Cloudflare no completa su validación en Cloud
  Run. Se conserva como no leído.
- `Descarga-Automatica-Reintento-1` y `-2`: el proveedor presentó un fallo
  técnico y el mensaje se procesará nuevamente de forma automática.

Los mensajes con etiquetas de error, manual o ignorado se excluyen de
ejecuciones posteriores. Para reintentar un correo, corrige la causa, elimina
su etiqueta de estado y consérvalo como no leído.

La firma esperada al iniciar esta versión es:

```text
VERSION_APP: V4.5.1-WETRANSFER-CONTROL-2026-07-30
```

## Despliegue

Para actualizar desde V4.5 consulta
[ACTUALIZACION_V4_5_1.md](ACTUALIZACION_V4_5_1.md). Para un despliegue nuevo
consulta [DESPLIEGUE_PASO_A_PASO.md](DESPLIEGUE_PASO_A_PASO.md).

## Seguridad

No subas `token.json`, `credentials.json`, `.env` ni secretos al repositorio.
El bucket temporal debe permanecer privado y la cuenta del job solo debe tener
el rol `roles/storage.objectUser` sobre ese bucket.

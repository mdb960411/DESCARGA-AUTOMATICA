# Descarga Automática Gmail → Google Drive V5

Trabajador persistente para Google Compute Engine que procesa correos de Gmail,
descarga adjuntos y enlaces de transferencia, y guarda los archivos obtenidos
en Google Drive.

Esta versión está preparada para trabajos de industria gráfica y archivos
grandes como `.ai`, `.ps`, `.eps`, `.indd`, `.psd`, `.tif`, `.pdf` y paquetes
comprimidos.

## Cambios principales de V5

- Usa una VM con IP estable y un perfil exclusivo de Chromium persistente.
- Conserva cookies, almacenamiento local y Service Workers entre ejecuciones.
- Ejecuta Chromium visible dentro de una pantalla virtual, sin abrir puertos.
- Descarga archivos grandes sobre el disco persistente, nunca en memoria.
- Impide dos ejecuciones simultáneas con un bloqueo local exclusivo.
- Reintenta fallos transitorios hasta cinco ejecuciones y separa los enlaces
  definitivamente caducados.
- Obtiene los JSON OAuth desde Secret Manager como archivos temporales privados.
- Guarda hasta veinte capturas privadas de diagnóstico cuando un proveedor
  cambia su interfaz.
- Publica las etiquetas de imagen `vm-v5`, `latest` y el SHA del commit.
- Incluye unidades de systemd para ejecución manual, cada 15 minutos o al
  encender la VM.

Consulta [ACTUALIZACION_V5_VM.md](ACTUALIZACION_V5_VM.md) para el diseño y
[DESPLIEGUE_VM_PASO_A_PASO.md](DESPLIEGUE_VM_PASO_A_PASO.md) para instalarlo.

## Base funcional heredada de V4.4

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
3. Descarga en `/data/downloads`, montado sobre el disco persistente de la VM.
4. Sube cada archivo a Google Drive de forma reanudable.
5. Etiqueta el correo según el resultado.
6. Elimina la copia temporal.

## Variables obligatorias

- `GOOGLE_CLIENT_SECRET_FILE` o `GOOGLE_CLIENT_SECRET_JSON`
- `GOOGLE_OAUTH_TOKEN_FILE` o `GOOGLE_OAUTH_TOKEN_JSON`
- `DRIVE_FOLDER_ID`
- `DOWNLOAD_DIR=/data/downloads`

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
BROWSER_PROFILE_DIR=/data/chrome-profile
STATE_DIR=/data/state
BROWSER_HEADLESS=false
BROWSER_PROVIDER_ATTEMPTS=2
MAX_MESSAGE_ATTEMPTS=5
BROWSER_HTTP_HANDOFF=true
EXCLUDE_ERROR_MESSAGES=true
EXCLUDE_IGNORED_MESSAGES=true
EXCLUDE_MANUAL_MESSAGES=true
BROWSER_ACTION_DIAGNOSTICS=true
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
- `Descarga-Automatica-Manual`: el enlace sigue requiriendo intervención
  humana, por ejemplo cuando Cloudflare no completa su validación en Cloud
  Run. Se conserva como no leído.
- `Descarga-Automatica-Reintento`: el fallo parece transitorio y volverá a
  intentarse automáticamente. Después del límite pasa a error.

Los mensajes con etiquetas de error, manual o ignorado se excluyen de
ejecuciones posteriores. Para reintentar un correo, corrige la causa, elimina
su etiqueta de estado y consérvalo como no leído.

## Despliegue recomendado

Consulta [DESPLIEGUE_VM_PASO_A_PASO.md](DESPLIEGUE_VM_PASO_A_PASO.md).

La guía anterior de Cloud Run permanece disponible solo como referencia y
como plan de reversión.

## Seguridad

No subas `token.json`, `credentials.json`, `.env` ni secretos al repositorio.
La VM obtiene las dos credenciales directamente desde Secret Manager durante
cada ejecución. El perfil del navegador y los diagnósticos permanecen en el
disco privado de la VM.

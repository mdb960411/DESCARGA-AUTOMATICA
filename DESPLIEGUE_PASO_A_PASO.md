# Despliegue paso a paso — V4.1

Configuración preparada para:

- Proyecto: `descarga-gmail-automatica`
- Región: `southamerica-west1`
- Bucket: `descarga-gmail-automatica-archivos-temp`
- Cuenta del job:
  `9486684574-compute@developer.gserviceaccount.com`

## 1. Configuración ya completada

- Bucket privado creado en Santiago.
- Control de versiones desactivado.
- Regla de eliminación automática de un día.
- Rol `Usuario de objetos de Storage` otorgado a la cuenta del job.

## 2. Subir esta versión a GitHub

No elimines el repositorio ni su configuración. Sube el contenido de esta
versión sobre los archivos existentes, sin copiar credenciales locales.
Comprueba que GitHub contenga:

- `app/`
- `Dockerfile`
- `requirements.txt`
- `cloudbuild.yaml`
- `README.md`

Espera a que el trigger de Cloud Build termine correctamente.

## 3. Montar el bucket en Cloud Run

1. Abre **Cloud Run → Jobs**.
2. Selecciona el job de descarga.
3. Presiona **Ver y editar configuración del job**.
4. Abre el contenedor `gmail-cloud-run-1`.
5. Entra en **Volúmenes**.
6. Presiona **Montar volumen**.
7. Selecciona **Bucket de Cloud Storage**.
8. Selecciona `descarga-gmail-automatica-archivos-temp`.
9. Usa como ruta de montaje:

   ```text
   /mnt/descargas
   ```

10. No marques **Solo lectura**.
11. Guarda el volumen.

## 4. Actualizar variables

En **Variables y secretos**, conserva todos los secretos existentes y agrega o
actualiza:

```text
DOWNLOAD_DIR=/mnt/descargas
MAX_FILE_SIZE_MB=8192
DOWNLOAD_CHUNK_SIZE_MB=4
UPLOAD_CHUNK_SIZE_MB=8
UPLOAD_RETRIES=3
DOWNLOAD_TIMEOUT_SECONDS=1800
BROWSER_HTTP_HANDOFF=true
EXCLUDE_ERROR_MESSAGES=true
ERROR_LABEL=Descarga-Automatica-Error
PARTIAL_LABEL=Descarga-Automatica-Parcial
IGNORED_LABEL=Descarga-Automatica-Ignorado
EXCLUDE_IGNORED_MESSAGES=true
```

Configura `ALLOWED_EXTENSIONS` con:

```text
.ai,.ait,.ps,.eps,.pdf,.zip,.rar,.7z,.indd,.idml,.psd,.psb,.tif,.tiff,.jpg,.jpeg,.png,.svg,.cdr,.afdesign,.afphoto,.xlsx,.xls,.xml,.csv,.doc,.docx
```

No reemplaces ni reveles:

- `GOOGLE_CLIENT_SECRET_JSON`
- `GOOGLE_OAUTH_TOKEN_JSON`
- `DRIVE_FOLDER_ID`

## 5. Recursos del job

Para la primera prueba:

- Memoria: `2 GiB`
- CPU: `1`
- Cantidad de tareas: `1`
- Paralelismo: `1`
- Reintentos máximos: `0`
- Tiempo máximo de la tarea: `2 horas`

La propia aplicación gestiona errores por correo. Dejar los reintentos del job
en cero evita que Google vuelva a iniciar inmediatamente todo el lote después
de un fallo del contenedor.

Si Chromium todavía supera la memoria durante una prueba, aumenta temporalmente
la memoria a `4 GiB`.

## 6. Seleccionar la nueva imagen

Selecciona la imagen generada por el último build correcto. Verifica que no
quede elegida una imagen anterior por etiqueta o digest.

Guarda con **Actualizar**, pero no marques todavía **Ejecutar el trabajo de
inmediato**.

## 7. Primera prueba controlada

1. Cambia temporalmente `MAX_EMAILS` a `1`.
2. Ejecuta el job manualmente.
3. Revisa que el log comience con:

   ```text
   VERSION_APP: V4.1-MULTIFILE-2026-07-23
   ```

4. Para SendGB, el log esperado incluye:

   ```text
   Enlace real capturado
   se cerrará Chromium
   Descargados ... GiB
   Subiendo ... %
   Estado=PROCESADO
   ```

5. Comprueba el archivo en Google Drive.
6. Comprueba que el bucket quede vacío después del correo.
7. Si todo funciona, restaura `MAX_EMAILS=20`.

## 8. Prueba específica de SendAllFiles

1. Conserva el correo válido que contiene `LINK 4.zip` y `LINK 2.zip`.
2. En Gmail, elimina de ese correo la etiqueta
   `Descarga-Automatica-Error`.
3. Déjalo como no leído.
4. Ejecuta el job.
5. El log esperado debe incluir:

   ```text
   [SENDALLFILES] Controles de descarga detectados: 2
   [SENDALLFILES] Iniciando archivo 1 de 2
   [SENDALLFILES] Iniciando archivo 2 de 2
   ```

6. Confirma que ambos archivos aparecen en Google Drive.

No reintentes los enlaces de WeTransfer o TransferNow ya caducados; la
aplicación los mantendrá en estado de error y mostrará el motivo cuando la
página del proveedor lo exponga.

## 9. Reintentar un correo con error

1. Abre Gmail.
2. Busca la etiqueta `Descarga-Automatica-Error`.
3. Corrige la causa o verifica que el enlace siga vigente.
4. Elimina la etiqueta de error del mensaje.
5. Déjalo como no leído.
6. Ejecuta nuevamente el job.

## 10. Correos sin archivos

La V4.1 crea automáticamente la etiqueta
`Descarga-Automatica-Ignorado`. Un correo sin adjuntos o enlaces útiles:

- no se considera error;
- no vuelve a procesarse;
- permanece sin leer.

Para volver a evaluarlo, elimina esa etiqueta.

## 11. Volver a la versión anterior

Si la prueba falla antes de procesar correos, edita el job y vuelve a seleccionar
la imagen anterior. Conserva el bucket; no interfiere con la versión anterior
mientras `DOWNLOAD_DIR` vuelva a apuntar a `/tmp/descargas`.

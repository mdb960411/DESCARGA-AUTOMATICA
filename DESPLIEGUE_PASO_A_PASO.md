# Despliegue paso a paso

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

Reemplaza el contenido del repositorio con esta versión, sin copiar archivos
locales de credenciales. Comprueba que GitHub contenga:

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
   VERSION_APP: V4-GRAPHIC-LARGE-FILES-2026-07-23
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

## 8. Reintentar un correo con error

1. Abre Gmail.
2. Busca la etiqueta `Descarga-Automatica-Error`.
3. Corrige la causa o verifica que el enlace siga vigente.
4. Elimina la etiqueta de error del mensaje.
5. Déjalo como no leído.
6. Ejecuta nuevamente el job.

## 9. Volver a la versión anterior

Si la prueba falla antes de procesar correos, edita el job y vuelve a seleccionar
la imagen anterior. Conserva el bucket; no interfiere con la versión anterior
mientras `DOWNLOAD_DIR` vuelva a apuntar a `/tmp/descargas`.

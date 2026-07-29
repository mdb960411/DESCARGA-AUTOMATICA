# Actualización rápida de V4.2 a V4.3

V4.3 conserva el bucket, la cuenta de servicio, los secretos y la descarga por
bloques de V4.2. No borres el repositorio, el job ni el bucket.

## 1. Subir los archivos a GitHub

1. Descomprime `DESCARGA-AUTOMATICA-V4.3.zip`.
2. Abre `mdb960411/DESCARGA-AUTOMATICA` en la rama `main`.
3. Presiona **Add file → Upload files**.
4. Arrastra todo el contenido de la carpeta descomprimida.
5. No subas `.env`, `token.json`, `credentials.json` ni otros secretos.
6. Confirma con **Commit changes**.

No elimines antes los archivos existentes. GitHub reemplazará los que tengan el
mismo nombre.

## 2. Esperar Cloud Build

1. Abre **Google Cloud → Cloud Build → Historial**.
2. Espera el build correspondiente al nuevo commit.
3. Continúa solamente cuando aparezca como **Correcta**.

## 3. Seleccionar la nueva imagen

1. Abre **Cloud Run → Trabajos → gmail-downloader**.
2. Presiona **Ver y editar la configuración del trabajo**.
3. En la imagen del contenedor, presiona **Seleccionar**.
4. Elige la imagen creada por el último build.
5. Conserva:
   - memoria `2 GiB`;
   - CPU `1`;
   - cantidad de tareas `1`;
   - paralelismo `1`;
   - reintentos `0`;
   - tiempo máximo `2 horas`;
   - volumen `/mnt/descargas`;
   - la misma cuenta de servicio.

## 4. Agregar las variables nuevas

En **Variables y secretos**, no borres las variables ni secretos existentes.
Agrega:

```text
MANUAL_LABEL=Descarga-Automatica-Manual
EXCLUDE_MANUAL_MESSAGES=true
BROWSER_ACTION_DIAGNOSTICS=true
```

Conserva además:

```text
DOWNLOAD_DIR=/mnt/descargas
MAX_EMAILS=20
MAX_FILE_SIZE_MB=8192
BROWSER_HTTP_HANDOFF=true
EXCLUDE_ERROR_MESSAGES=true
EXCLUDE_IGNORED_MESSAGES=true
```

Presiona **Actualizar**.

## 5. Verificar la versión

Ejecuta el job con un único correo nuevo y comprueba que el log comience con:

```text
VERSION_APP: V4.3-PROVIDER-RECOVERY-2026-07-28
```

Si aparece V4.2, vuelve a editar el job y selecciona la imagen del último build.

## 6. Probar proveedores

Para WeTransfer, TransferNow y SwissTransfer:

1. Envía una transferencia nueva y pequeña.
2. Deja el correo sin leer.
3. Configura temporalmente `MAX_EMAILS=1`.
4. Ejecuta el job.
5. Comprueba el archivo en Drive.
6. Repite con el siguiente proveedor.

Cuando termines, restaura `MAX_EMAILS=20`.

## 7. SendAllFiles y Cloudflare

Si Cloudflare vuelve a quedar pendiente, V4.3 mostrará:

```text
[SENDALLFILES] ACCION_MANUAL: ...
[CORREO] Estado=MANUAL. ...
```

El correo recibirá `Descarga-Automatica-Manual`, permanecerá no leído y no se
reintentará en cada ejecución. Los archivos deben descargarse manualmente desde
un navegador donde Cloudflare haya completado su validación.

Para volver a probarlo, elimina la etiqueta manual y deja el correo sin leer.

## 8. Enviar un diagnóstico

Si un proveedor nuevo falla, copia desde el log:

```text
[PROVEEDOR] Diagnóstico seguro: ...
[PROVEEDOR] Acción visible 1: ...
[CORREO] Estado=...
[RESUMEN] Estado=...
```

Esas líneas no contienen el enlace privado completo.

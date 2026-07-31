# Actualización de V4.5.4 a V4.5.5

Esta versión responde al registro donde SendAllFiles mantuvo Turnstile
pendiente en tres sesiones y WeTransfer no mostró la tarjeta de descarga en
quince sesiones consecutivas, aunque ambos enlaces funcionaban en Chrome de
escritorio.

## 1. Qué cambia

- WeTransfer y SendAllFiles ejecutan Chromium en modo visible.
- Cloud Run crea una pantalla virtual de 1280 × 800 mediante Xvfb.
- Las sesiones bloqueadas se reemplazan después de 30 segundos.
- Los demás proveedores continúan usando su navegador liviano actual.
- Gmail, Drive, OAuth, el bucket y Cloud Scheduler no cambian.

## 2. Subir la versión

1. Descomprime `DESCARGA-AUTOMATICA-V4.5.5.zip`.
2. Sube su contenido sobre los archivos actuales del repositorio.
3. No elimines el repositorio.
4. No subas `token.json`, `CREDENTIALS.json`, `.env` ni secretos.
5. Espera que Cloud Build termine en estado **Correcta**.

El nuevo Dockerfile instala `xvfb` y `xauth`; por eso esta compilación puede
tardar un poco más que las anteriores.

## 3. Actualizar Cloud Run

1. Abre **Cloud Run → Trabajos → gmail-downloader**.
2. Selecciona **Ver y editar la configuración del trabajo**.
3. Selecciona la imagen generada por el último build correcto.
4. Conserva secretos, volumen, cuenta de servicio, CPU y memoria.
5. En **Variables y secretos**, configura:

   ```text
   WETRANSFER_DOWNLOAD_ATTEMPTS=3
   SENDALLFILES_DOWNLOAD_ATTEMPTS=3
   TRANSIENT_RETRY_RUNS=5
   ```

   Los tres intentos internos evitan trabajos de más de media hora. Los cinco
   reintentos programados conservan margen para los correos ya pendientes.

6. Presiona **Actualizar**.

## 4. Preparar los correos pendientes

- No elimines las etiquetas `Descarga-Automatica-Reintento-*`.
- Conserva los correos como no leídos.
- Si SendAllFiles todavía conserva `Descarga-Automatica-Manual`, elimina
  únicamente esa etiqueta y déjalo como no leído.

## 5. Primera prueba

1. Verifica que no exista otra ejecución activa.
2. Ejecuta el job manualmente.
3. El registro debe comenzar con:

   ```text
   VERSION_APP: V4.5.5-VIRTUAL-DISPLAY-2026-07-31
   ```

4. Para WeTransfer y SendAllFiles debe aparecer:

   ```text
   Navegador visible virtual activo
   Modo compatible activo
   ```

5. El resultado correcto termina con:

   ```text
   Descargado: ...
   [DRIVE] Subido: ...
   [CORREO] Estado=PROCESADO
   ```

## 6. Si continúa pendiente

Conserva el correo y envía el nuevo CSV. No aumentes los intentos internos por
encima de tres: si el modo visible tampoco recibe la tarjeta, necesitaremos
diagnosticar la respuesta que el proveedor entrega a la red de Cloud Run.

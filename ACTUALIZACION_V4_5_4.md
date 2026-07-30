# Actualización de V4.5.3 a V4.5.4

Esta versión corrige el falso estado manual observado en SendAllFiles. En un
navegador normal Cloudflare puede mostrar `¡Operación exitosa!` sin solicitar
ninguna acción, aunque una sesión concreta de Cloud Run quede temporalmente
pendiente.

## 1. Qué cambia

- SendAllFiles abre hasta tres navegadores independientes.
- Una validación pendiente de Cloudflare se considera transitoria.
- El correo pasa a reintento automático si ninguna sesión consigue mostrar
  los botones de descarga.
- Nueva variable opcional:

  ```text
  SENDALLFILES_DOWNLOAD_ATTEMPTS=3
  ```

No cambia Gmail, Drive, OAuth, el bucket ni Cloud Scheduler.

## 2. Subir la versión

1. Descomprime `DESCARGA-AUTOMATICA-V4.5.4.zip`.
2. Sube su contenido sobre los archivos actuales del repositorio.
3. No elimines el repositorio.
4. No subas `token.json`, `CREDENTIALS.json`, `.env` ni secretos.
5. Espera que Cloud Build termine en estado **Correcta**.

## 3. Actualizar Cloud Run

1. Abre **Cloud Run → Trabajos → gmail-downloader**.
2. Selecciona **Ver y editar la configuración del trabajo**.
3. Selecciona la imagen generada por el último build correcto.
4. En **Variables y secretos**, agrega:

   ```text
   SENDALLFILES_DOWNLOAD_ATTEMPTS=3
   ```

5. Conserva todas las demás variables, secretos, recursos y volúmenes.
6. Presiona **Actualizar**.

## 4. Recuperar el correo que quedó manual

1. Abre Gmail.
2. Busca el correo de SendAllFiles con la etiqueta
   `Descarga-Automatica-Manual`.
3. Elimina únicamente esa etiqueta.
4. Marca el correo como no leído.
5. Ejecuta el job.

## 5. Verificación

El registro debe comenzar con:

```text
VERSION_APP: V4.5.4-SENDALLFILES-AUTO-RETRY-2026-07-30
```

Si la primera sesión no completa Cloudflare, debe aparecer:

```text
[SENDALLFILES] Intento 1 de 3
[SENDALLFILES] Fallo transitorio; se abrirá un navegador nuevo
[SENDALLFILES] Intento 2 de 3
```

El resultado correcto termina con:

```text
[SENDALLFILES] Descargado: ...
[DRIVE] Subido: ...
[CORREO] Estado=PROCESADO
```

# Actualización de V4.4 a V4.5

V4.5 corrige los fallos intermitentes observados al volver a procesar enlaces
de WeTransfer y prepara el job para ejecutarse cada 15 minutos con Cloud
Scheduler.

No debes recrear el bucket, el job, el token OAuth, los secretos, la cuenta de
servicio ni el activador.

## Qué corrige

- WeTransfer realiza hasta tres intentos con un navegador nuevo cuando el
  primer intento no encuentra el control de descarga.
- Los enlaces realmente caducados o protegidos con contraseña no se repiten.
- Un fallo técnico se conserva como reintento pendiente y vuelve a entrar en
  las siguientes ejecuciones del programador.
- Después de tres ejecuciones fallidas, el correo pasa a la etiqueta de error.
- Drive reconoce duplicados por transferencia y también por nombre, tamaño y
  MD5. Esto permite detectar archivos subidos previamente por V4.4.
- Las etiquetas de Gmail se verifican después de aplicarlas.
- Las confirmaciones de envío de TransferNow se ignoran; solo se procesa la
  notificación destinada al receptor.
- Un bloqueo persistente en el bucket impide que dos ejecuciones del job
  procesen correos simultáneamente.

## 1. Pausar temporalmente el programador

1. Abre **Cloud Scheduler**.
2. Selecciona `gmail-downloader-scheduler-trigger`.
3. Presiona **Pausar**.

Esto evita que la versión anterior se ejecute durante la actualización.

## 2. Subir V4.5 a GitHub

1. Descomprime `DESCARGA-AUTOMATICA-V4.5.zip`.
2. Abre el repositorio `mdb960411/DESCARGA-AUTOMATICA`, rama `main`.
3. Presiona **Add file → Upload files**.
4. Arrastra todo el contenido de la carpeta descomprimida.
5. No borres primero los archivos existentes.
6. No subas `.env`, `token.json`, `credentials.json` ni otros secretos.
7. Confirma con **Commit changes**.

## 3. Esperar Cloud Build

1. Abre **Google Cloud → Cloud Build → Historial**.
2. Espera que la compilación del nuevo commit aparezca como **Correcta**.

## 4. Seleccionar la imagen nueva

1. Abre **Cloud Run → Trabajos → gmail-downloader**.
2. Presiona **Ver y editar la configuración del trabajo**.
3. En la imagen del contenedor, presiona **Seleccionar**.
4. Elige la imagen correspondiente al último build.
5. No cambies las variables, secretos, volumen ni cuenta de servicio.
6. Presiona **Actualizar**.

Las variables nuevas tienen valores predeterminados y no es obligatorio
agregarlas en Cloud Run.

## 5. Preparar los dos correos que fallaron

En Gmail localiza:

- `preprensa@inser-impresores.cl sent you dfdfd via WeTransfer`;
- `jvenegas@inser-impresores.cl sent you 621260 via WeTransfer`.

En ambos mensajes:

1. elimina la etiqueta `Descarga-Automatica-Error`;
2. elimina `Descarga-Automatica-Parcial` si aparece;
3. márcalos como **no leídos**.

No elimines los archivos que ya están en Drive: V4.5 debe reconocerlos como
duplicados.

## 6. Ejecutar una prueba manual

1. Abre **Cloud Run → Trabajos → gmail-downloader**.
2. Presiona **Ejecutar**.
3. Espera que termine.
4. Revisa el log.

La primera línea debe ser:

```text
VERSION_APP: V4.5-RETRY-IDEMPOTENCY-2026-07-29
```

Los reintentos de WeTransfer se verán así:

```text
[WETRANSFER] Intento 1 de 3
[WETRANSFER] Fallo transitorio; se abrirá un navegador nuevo
[WETRANSFER] Intento 2 de 3
```

Cuando un archivo ya exista:

```text
[DRIVE] Duplicado confirmado por contenido
[DRIVE] Ya existía; no se volverá a subir
```

Y cada estado de Gmail debe terminar con:

```text
[GMAIL] Etiquetas verificadas
```

## 7. Reactivar el programador

Cuando la prueba termine:

1. vuelve a **Cloud Scheduler**;
2. selecciona `gmail-downloader-scheduler-trigger`;
3. presiona **Reanudar**.

El programa `*/15 * * * *` lo ejecutará en los minutos 00, 15, 30 y 45.

## Variables opcionales nuevas

No es necesario agregarlas. Estos son sus valores predeterminados:

```text
WETRANSFER_DOWNLOAD_ATTEMPTS=3
PROVIDER_RETRY_DELAY_SECONDS=2
TRANSIENT_RETRY_RUNS=3
RETRY_LABEL=Descarga-Automatica-Reintento
EXECUTION_LOCK_TTL_SECONDS=3600
```

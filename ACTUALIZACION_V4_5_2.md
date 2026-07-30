# Actualización de V4.5.1 a V4.5.2

Esta versión responde al caso en que TransferNow muestra `Download file`,
abre una segunda etapa y no inicia el archivo. La aplicación ahora repite
internamente ese enlace hasta tres veces, cada vez con un navegador limpio.

## 1. Subir los archivos

Descomprime `DESCARGA-AUTOMATICA-V4.5.2.zip` y sube su contenido sobre los
archivos actuales del repositorio. No elimines el repositorio, los secretos,
el bucket, el job ni el activador de Cloud Scheduler.

No subas `token.json`, `CREDENTIALS.json`, `.env` ni ningún secreto.

## 2. Esperar Cloud Build

Espera que la compilación termine en estado **Correcta** y luego selecciona
la nueva imagen en el job `gmail-downloader`.

## 3. Variable del job

En **Variables y secretos**, agrega:

```text
TRANSFERNOW_DOWNLOAD_ATTEMPTS=3
```

Conserva también:

```text
WETRANSFER_DOWNLOAD_ATTEMPTS=3
PROVIDER_RETRY_DELAY_SECONDS=2
TRANSIENT_RETRY_RUNS=3
```

No cambies los secretos de OAuth.

## 4. Verificar la versión

Ejecuta el job y comprueba al inicio:

```text
VERSION_APP: V4.5.2-TRANSFERNOW-RETRY-2026-07-30
```

Para un fallo transitorio de TransferNow, el registro esperado incluye:

```text
[TRANSFERNOW] Intento 1 de 3
[TRANSFERNOW] Fallo transitorio; se abrirá un navegador nuevo en 2s
[TRANSFERNOW] Intento 2 de 3
```

Si un intento posterior funciona, aparecerá:

```text
[TRANSFERNOW] Descarga recuperada en el intento 2
```

## 5. Correo que ya quedó pendiente

No elimines la etiqueta `Descarga-Automatica-Reintento-1` del correo
`MJ327_114.pdf`. Déjalo sin leer. La próxima ejecución lo seleccionará como
intento externo 2 de 3; dentro de esa ejecución V4.5.2 tendrá además hasta
tres navegadores limpios para completar TransferNow.

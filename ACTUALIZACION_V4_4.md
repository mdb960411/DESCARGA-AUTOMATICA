# Actualización rápida de V4.3 a V4.4

V4.4 conserva el bucket, el job, la cuenta de servicio, el token OAuth y todas
las variables actuales. No elimines el repositorio ni vuelvas a crear los
recursos de Google Cloud.

## Qué corrige

El log de V4.3 mostró cinco archivos subidos que no pertenecían a los trabajos:
dos `unnamed.png` y tres `ot_guard_logo.svg`. Eran imágenes de correos y del
aviso de cookies de WeTransfer.

V4.4:

- ignora recursos incrustados, logos, píxeles, cookies y analítica;
- exige evidencia fuerte antes de usar una respuesta capturada en la red;
- acepta la pantalla intermedia de condiciones de WeTransfer;
- evita cancelar las URLs de descarga de un solo uso de WeTransfer;
- trata las variantes de enlace de un correo de WeTransfer como alternativas;
- continúa con TransferNow si el primer clic abre otra pestaña;
- descarta anuncios y controles no interactivos.

## 1. Subir V4.4 a GitHub

1. Descomprime `DESCARGA-AUTOMATICA-V4.4.zip`.
2. Abre el repositorio `mdb960411/DESCARGA-AUTOMATICA`, rama `main`.
3. Presiona **Add file → Upload files**.
4. Arrastra todo el contenido de la carpeta descomprimida.
5. No subas `.env`, `token.json`, `credentials.json` ni otros secretos.
6. Confirma con **Commit changes**.

No borres primero los archivos del repositorio. GitHub reemplazará los que
tengan el mismo nombre y agregará los nuevos.

## 2. Esperar Cloud Build

1. Abre **Google Cloud → Cloud Build → Historial**.
2. Espera la compilación del nuevo commit.
3. Continúa cuando el estado sea **Correcta**.

## 3. Seleccionar la imagen nueva

1. Abre **Cloud Run → Trabajos → gmail-downloader**.
2. Presiona **Ver y editar la configuración del trabajo**.
3. En la imagen del contenedor, presiona **Seleccionar**.
4. Elige la imagen del último build.
5. No cambies las variables, secretos, volumen ni cuenta de servicio.
6. Presiona **Actualizar**.

## 4. Limpiar los falsos archivos anteriores

En la carpeta de destino de Google Drive, elimina:

- `unnamed.png` — dos archivos;
- `ot_guard_logo.svg` — tres archivos.

Son recursos web detectados por V4.3, no archivos enviados por clientes. Si
mantienes esos archivos, la prevención de duplicados puede volver a
reconocerlos al reintentar los mismos mensajes.

## 5. Probar con correos nuevos

1. Envía una transferencia nueva y pequeña de WeTransfer.
2. Déjala sin leer.
3. Configura temporalmente `MAX_EMAILS=1`.
4. Ejecuta el job.
5. Comprueba el archivo real en Drive.
6. Repite con una transferencia nueva de TransferNow.
7. Restaura `MAX_EMAILS=20`.

Usa enlaces nuevos; los anteriores pueden haber caducado.

## 6. Verificar el log

La primera línea de la aplicación debe ser:

```text
VERSION_APP: V4.4-FALSE-POSITIVE-GUARD-2026-07-29
```

No deben aparecer subidas de:

```text
unnamed.png
ot_guard_logo.svg
```

Para una descarga correcta de WeTransfer debe aparecer:

```text
[WETRANSFER] Descarga nativa del navegador activa
[WETRANSFER] Descargado: NOMBRE_REAL...
[DRIVE] Subido: NOMBRE_REAL...
[CORREO] Estado=PROCESADO
```

## 7. Reintentar un correo anterior

Es preferible usar una transferencia nueva. Si necesitas reintentar un mensaje
anterior:

1. elimina sus etiquetas `Descarga-Automatica-Error`,
   `Descarga-Automatica-Parcial` o `Descarga-Automatica-Procesado`;
2. márcalo como no leído;
3. verifica que el enlace siga vigente;
4. ejecuta el job con `MAX_EMAILS=1`.

# Actualización de V4.5 a V4.5.1

Esta actualización corrige el caso observado en WeTransfer donde la página se
abre, pero el archivo no comienza a descargarse.

El log mostró que Chromium encontró el enlace publicitario `Sé Ultimate` antes
de que apareciera el botón verdadero. V4.5.1 descarta ese enlace, espera hasta
45 segundos el control real y mantiene los tres intentos con navegadores
nuevos.

No debes recrear el bucket, el token OAuth, los secretos, la cuenta de servicio
ni el programador.

## 1. Esperar la ejecución activa

1. Abre **Cloud Run → Trabajos → gmail-downloader → Historial**.
2. Verifica que no exista una ejecución con estado **Activa**.
3. Si existe, espera que termine antes de actualizar.

El estado `OMITIDA_EJECUCION_ACTIVA` significa que el bloqueo de seguridad
evitó que dos ejecuciones procesaran los mismos correos simultáneamente.

## 2. Pausar el programador

1. Abre **Cloud Scheduler**.
2. Selecciona `gmail-downloader-scheduler-trigger`.
3. Presiona **Pausar**.

## 3. Subir V4.5.1 a GitHub

1. Descomprime `DESCARGA-AUTOMATICA-V4.5.1.zip`.
2. Abre el repositorio `mdb960411/DESCARGA-AUTOMATICA`, rama `main`.
3. Presiona **Add file → Upload files**.
4. Arrastra el contenido de la carpeta descomprimida.
5. No borres primero los archivos existentes.
6. No subas `.env`, `token.json`, `credentials.json` ni otros secretos.
7. Confirma con **Commit changes**.

## 4. Seleccionar la imagen nueva

1. Espera que **Cloud Build** termine correctamente.
2. Abre **Cloud Run → Trabajos → gmail-downloader**.
3. Presiona **Ver y editar la configuración del trabajo**.
4. Selecciona la imagen correspondiente al último build.
5. No cambies variables, secretos, volumen ni cuenta de servicio.
6. Presiona **Actualizar**.

## 5. Probar el correo

Si el mensaje terminó con `Descarga-Automatica-Error`, elimina esa etiqueta y
márcalo como no leído. Si conserva una etiqueta
`Descarga-Automatica-Reintento-1` o `-2`, basta con mantenerlo no leído.

Ejecuta el job manualmente. La primera línea debe ser:

```text
VERSION_APP: V4.5.1-WETRANSFER-CONTROL-2026-07-30
```

El comportamiento esperado es:

```text
[WETRANSFER] Intento 1 de 3
[WETRANSFER] Esperando interfaz dinámica
[WETRANSFER] Interfaz de descarga lista
[WETRANSFER] Descarga iniciada
```

El enlace `Sé Ultimate` ya no debe aparecer como candidato inteligente.

## 6. Reactivar el programador

Cuando la prueba termine correctamente:

1. vuelve a **Cloud Scheduler**;
2. selecciona `gmail-downloader-scheduler-trigger`;
3. presiona **Reanudar**.

El programa `*/15 * * * *` continuará ejecutándose cada 15 minutos.

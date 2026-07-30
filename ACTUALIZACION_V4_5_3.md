# Actualización de V4.5.2 a V4.5.3

Esta versión corrige el flujo que muestran los enlaces `dfdfd`, `621260` y
`621200`: WeTransfer presenta un panel lateral con `Abrir` y `Descargar`, pero
el primer clic puede abrir etapas adicionales antes de iniciar el archivo.

## 1. Qué cambia

- Perfil de Chromium compatible con la aplicación dinámica de WeTransfer.
- Espera de hasta 75 segundos para que aparezca el panel lateral.
- Hasta cinco etapas internas de navegación.
- Reconocimiento del control `Ir a la transferencia`.
- Captura de descargas que comienzan de manera asíncrona.

No cambia Gmail, Drive, el bucket, OAuth ni Cloud Scheduler.

## 2. Subir la versión

1. Descomprime `DESCARGA-AUTOMATICA-V4.5.3.zip`.
2. Sube su contenido sobre los archivos actuales del repositorio.
3. No elimines el repositorio.
4. No subas `token.json`, `CREDENTIALS.json`, `.env` ni secretos.
5. Espera que Cloud Build termine en estado **Correcta**.

## 3. Actualizar Cloud Run

1. Abre **Cloud Run → Trabajos → gmail-downloader**.
2. Selecciona **Ver y editar la configuración del trabajo**.
3. Selecciona la imagen generada por el último build correcto.
4. Conserva todas las variables, secretos, recursos y volúmenes actuales.
5. Presiona **Actualizar**.

No es necesario crear variables nuevas para V4.5.3.

## 4. Correos pendientes

Conserva como no leídos los correos `dfdfd`, `621260` y `621200`. No elimines
las etiquetas `Descarga-Automatica-Reintento-*`; la nueva versión continuará
con el siguiente intento programado.

## 5. Verificación

El registro debe comenzar con:

```text
VERSION_APP: V4.5.3-WETRANSFER-MULTISTEP-2026-07-30
```

En WeTransfer puede aparecer una secuencia como:

```text
[WETRANSFER] Modo compatible activo
[WETRANSFER] Candidato inteligente etapa 1
[WETRANSFER] La acción avanzó la interfaz
[WETRANSFER] Candidato inteligente etapa 2
```

El resultado correcto termina con:

```text
[WETRANSFER] Descargado: ...
[DRIVE] Subido: ...
[CORREO] Estado=PROCESADO
```

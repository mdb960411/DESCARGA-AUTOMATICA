# Actualización rápida de V4.1 a V4.2

El registro confirmó que V4.1 esperó aproximadamente 65 segundos, pero el
navegador de Cloud Run nunca mostró los botones que sí aparecen en Chrome.
V4.2 habilita las funciones web que SendAllFiles necesita y conserva su sesión
validada durante la descarga.

No borres el repositorio, el bucket, el job ni sus variables.

## 1. Subir V4.2 a GitHub

1. Descomprime `DESCARGA-AUTOMATICA-V4.2.zip`.
2. Abre `mdb960411/DESCARGA-AUTOMATICA` en la rama `main`.
3. Presiona **Add file → Upload files**.
4. Abre la carpeta descomprimida `DESCARGA-AUTOMATICA-V4.2`.
5. Arrastra **todo su contenido**, no la carpeta exterior.
6. Confirma con **Commit changes**.

Los archivos existentes serán reemplazados. No necesitas eliminarlos antes.

## 2. Esperar Cloud Build

1. Abre **Google Cloud → Cloud Build → Historial**.
2. Espera la compilación correspondiente al nuevo commit.
3. Continúa cuando aparezca como **Correcta**.

## 3. Actualizar la imagen del job

1. Abre **Cloud Run → Trabajos → gmail-downloader**.
2. Selecciona **Ver y editar la configuración del trabajo**.
3. En la imagen del contenedor, presiona **Seleccionar**.
4. Elige la imagen creada por el último commit.
5. Conserva:
   - memoria `2 GiB`;
   - CPU `1`;
   - volumen `/mnt/descargas`;
   - tiempo máximo de `2 horas`;
   - reintentos `0`;
   - la misma cuenta de servicio y variables.
6. Presiona **Actualizar**.

## 4. Preparar una sola prueba

1. En Gmail, busca el correo vigente de SendAllFiles que contiene
   `LINK 4.zip` y `LINK 2.zip`.
2. Elimina únicamente su etiqueta `Descarga-Automatica-Error`.
3. Déjalo como no leído.
4. No habilites correos cuyos enlaces estén caducados.
5. Configura temporalmente `MAX_EMAILS=1`.

## 5. Ejecutar

El log debe comenzar con:

```text
VERSION_APP: V4.2-SENDALLFILES-COMPAT-2026-07-24
[SENDALLFILES] Modo compatible activo: User-Agent nativo y Service Workers habilitados
```

Después se espera:

```text
[SENDALLFILES] Controles de descarga detectados: 2
[SENDALLFILES] Iniciando archivo 1 de 2
[SENDALLFILES] Descarga nativa del navegador activa
```

La descarga nativa puede permanecer varios minutos sin mostrar porcentajes.
Chromium está escribiendo directamente en el volumen externo y al terminar
aparecerá:

```text
[SENDALLFILES] Descargado: LINK 4.zip (...)
[SENDALLFILES] Iniciando archivo 2 de 2
[SENDALLFILES] Descargado: LINK 2.zip (...)
[CORREO] Estado=PROCESADO. Archivos completados=2
```

## 6. Si aún falla

Copia solamente esta línea del nuevo registro:

```text
[SENDALLFILES] Diagnóstico seguro: estado=... marcos=... acciones_visibles=... service_workers=... turnstile=...
```

Esa línea no contiene el enlace ni los nombres de los archivos y permitirá
distinguir si la aplicación web no cargó, si la validación quedó pendiente o
si SendAllFiles cambió nuevamente su interfaz.

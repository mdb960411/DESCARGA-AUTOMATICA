# Actualización rápida de V4 a V4.1

No debes borrar el repositorio, el bucket, el job ni las variables actuales.
Esta actualización solo reemplaza el código y selecciona la nueva imagen.

## 1. Subir el código a GitHub

1. Descomprime `DESCARGA-AUTOMATICA-V4.1.zip`.
2. Abre el repositorio `mdb960411/DESCARGA-AUTOMATICA`.
3. En la rama `main`, presiona **Add file → Upload files**.
4. Abre la carpeta descomprimida `DESCARGA-AUTOMATICA-V4.1`.
5. Arrastra **su contenido** a GitHub. Debes ver `app`, `tests`,
   `Dockerfile`, `README.md` y los demás archivos en la raíz.
6. No subas una carpeta adicional dentro del repositorio.
7. Confirma con **Commit changes** directamente en `main`.

Los archivos que ya existan serán reemplazados. No elimines previamente el
contenido del repositorio.

## 2. Esperar la compilación

1. Abre **Google Cloud → Cloud Build → Historial**.
2. Espera la compilación activada por el commit de GitHub.
3. Continúa únicamente cuando aparezca como **Correcta**.

## 3. Seleccionar la nueva imagen

1. Abre **Cloud Run → Trabajos → gmail-downloader**.
2. Presiona **Ver y editar la configuración del trabajo**.
3. En **URL de la imagen del contenedor**, presiona **Seleccionar**.
4. Elige la imagen creada por la compilación recién terminada.
5. Verifica que el identificador coincida con el commit nuevo de GitHub.
6. No cambies el volumen `/mnt/descargas`, la memoria de `2 GiB`, la CPU ni la
   cuenta de servicio.
7. Presiona **Actualizar**.

La V4.1 ya contiene valores predeterminados para:

```text
IGNORED_LABEL=Descarga-Automatica-Ignorado
EXCLUDE_IGNORED_MESSAGES=true
```

No es obligatorio agregarlos manualmente a Cloud Run.

## 4. Preparar la prueba de SendAllFiles

1. En Gmail, busca el correo válido de SendAllFiles que contiene dos archivos.
2. Elimina **solo de ese correo** la etiqueta
   `Descarga-Automatica-Error`.
3. Confirma que esté marcado como **no leído**.
4. No quites la etiqueta de error a los correos de WeTransfer o TransferNow
   cuyos enlaces ya caducaron.

## 5. Ejecutar y comprobar

1. Ejecuta manualmente `gmail-downloader`.
2. El inicio del log debe mostrar:

   ```text
   VERSION_APP: V4.1-MULTIFILE-2026-07-23
   ```

3. Para SendAllFiles se espera:

   ```text
   [SENDALLFILES] Controles de descarga detectados: 2
   [SENDALLFILES] Iniciando archivo 1 de 2
   [SENDALLFILES] Iniciando archivo 2 de 2
   ```

4. Luego deben aparecer dos secuencias de descarga y subida a Drive.
5. El correo debe terminar con:

   ```text
   [CORREO] Estado=PROCESADO. Archivos completados=2
   ```

6. Comprueba los dos archivos en Google Drive.

Si el enlace ya caducó durante la prueba, el log lo indicará y será necesario
generar una transferencia nueva de SendAllFiles.

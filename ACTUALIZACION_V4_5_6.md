# Actualización de V4.5.5 a V4.5.6

Esta versión corrige el arranque observado el 31 de julio: Cloud Storage se
montó correctamente, pero el contenedor no alcanzó a iniciar Python ni a
registrar `VERSION_APP`.

## Qué cambia

- Se reemplaza el envoltorio `xvfb-run` por un arranque explícito de Xvfb.
- Xvfb dispone de 10 segundos para crear la pantalla virtual.
- El registro muestra cada etapa del inicio y un error concreto si Xvfb falla.
- Al finalizar el trabajo se cierran tanto Python como Xvfb.
- No cambian Gmail, Drive, OAuth, el bucket, las etiquetas ni los proveedores.

## Antes de desplegar

1. Pausa temporalmente el activador de Cloud Scheduler.
2. Cancela todas las ejecuciones de `gmail-downloader` que sigan activas.
3. Espera hasta que Cloud Run muestre cero ejecuciones activas.

## Despliegue

1. Descomprime `DESCARGA-AUTOMATICA-V4.5.6.zip`.
2. Sube su contenido sobre los archivos actuales del repositorio.
3. No elimines el repositorio.
4. No subas `token.json`, `CREDENTIALS.json`, `.env` ni secretos.
5. Espera que Cloud Build termine en estado **Correcta**.
6. En Cloud Run, edita `gmail-downloader` y selecciona la imagen del último
   build correcto.
7. Conserva todas las variables, secretos, volumen, cuenta de servicio, CPU y
   memoria actuales.
8. Presiona **Actualizar**.

## Primera prueba

Ejecuta el trabajo una sola vez de forma manual. El inicio correcto debe mostrar
estas líneas en menos de 10 segundos:

```text
[INICIO] Iniciando pantalla virtual Xvfb
[INICIO] Pantalla virtual lista en DISPLAY=:...
[INICIO] Iniciando aplicación Python
VERSION_APP: V4.5.6-XVFB-STARTUP-GUARD-2026-07-31
```

Si Xvfb no puede arrancar, el trabajo ahora finalizará con error en vez de
quedar activo sin avanzar.

Cuando la prueba manual termine correctamente, reanuda Cloud Scheduler.

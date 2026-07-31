# Actualización V5: trabajador persistente en Compute Engine

## Motivo del cambio

Cloud Run crea entornos temporales. Aunque el código cerraba Chromium antes de
transferir los archivos grandes por HTTP, proveedores como WeTransfer y
SendAllFiles seguían viendo un navegador nuevo, una dirección variable y una
sesión vacía en cada intento. Agregar selectores no solucionaba esa diferencia
de entorno.

V5 mantiene la automatización en GitHub y Google Cloud, pero ejecuta el
contenedor dentro de una VM con:

- dirección IP pública estable;
- disco persistente de 50 GB;
- perfil exclusivo de Chromium persistente;
- pantalla virtual para ejecutar Chromium en modo visible;
- una única ejecución activa;
- reintentos limitados e idempotencia en Google Drive.

## Flujo de V5

1. Cloud Build construye la imagen desde GitHub.
2. Artifact Registry publica `gmail-cloud-run:vm-v5`.
3. La VM obtiene los dos JSON OAuth desde Secret Manager.
4. Docker monta tres carpetas persistentes del disco de la VM.
5. La aplicación procesa los correos de forma secuencial.
6. Chromium conserva su sesión entre enlaces y ejecuciones.
7. Cada archivo se sube a Drive y su copia temporal se elimina.
8. Los fallos transitorios se reintentan; los enlaces caducados terminan como
   error sin crear un ciclo infinito.

## Directorios persistentes

| Host de la VM | Contenedor | Uso |
| --- | --- | --- |
| `/var/lib/gmail-downloader/chrome-profile` | `/data/chrome-profile` | Cookies, almacenamiento local y Service Workers |
| `/var/lib/gmail-downloader/downloads` | `/data/downloads` | Archivos grandes mientras se suben a Drive |
| `/var/lib/gmail-downloader/state` | `/data/state` | Bloqueo, reintentos y diagnósticos |

## Seguridad

- El repositorio no contiene tokens ni credenciales.
- Los secretos existen unos minutos bajo `/run` y se eliminan al terminar.
- No se habilitan puertos HTTP o HTTPS en la VM.
- Chromium usa un perfil separado del navegador personal del usuario.
- Los diagnósticos visuales permanecen en el disco privado y se limita su
  cantidad.

## Estrategia de puesta en marcha

1. Conservar el trabajo de Cloud Run sin borrarlo.
2. Publicar V5 y ejecutar una prueba manual en la VM.
3. Verificar enlaces nuevos de WeTransfer, SendAllFiles y TransferNow.
4. Activar la ejecución cada 15 minutos.
5. Después de varios días estables, configurar encendido programado y apagado
   automático para reducir costos.

Una IP estable y un perfil persistente mejoran la compatibilidad, pero ningún
servicio externo garantiza que su interfaz privada no vuelva a cambiar. Por
eso V5 conserva diagnósticos y estados de reintento sin exponer los enlaces en
los registros.

# Despliegue V5.1 en la VM

Esta guía supone que ya existe la VM `gmail-downloader-worker`, que Docker está
instalado y que la cuenta de servicio puede leer Secret Manager y Artifact
Registry.

## 1. Publicar el código

Sube a la rama `main` de GitHub todos los archivos de este paquete. No subas
`token.json`, `CREDENTIALS.json`, `.env` ni ninguna clave.

El activador de Cloud Build debe terminar correctamente y publicar:

```text
southamerica-west1-docker.pkg.dev/descarga-gmail-automatica/gmail-downloader/gmail-cloud-run:vm-v5
```

## 2. Obtener el repositorio en la VM

En SSH:

```bash
sudo apt-get update
sudo apt-get install -y git
cd /tmp
git clone https://github.com/mdb960411/DESCARGA-AUTOMATICA.git gmail-downloader-v5
cd gmail-downloader-v5
```

Si esa carpeta ya existe, entra en ella y ejecuta `git pull` en vez de volver a
clonarla.

## 3. Instalar el trabajador

```bash
sudo bash vm/install.sh
```

El instalador conserva cualquier configuración existente y todavía no inicia
el proceso.

## 4. Configurar la carpeta de Drive

Abre el archivo privado de configuración:

```bash
sudo nano /etc/gmail-downloader/worker.env
```

Reemplaza solamente:

```text
DRIVE_FOLDER_ID=REEMPLAZAR_CON_ID_DE_CARPETA_DRIVE
```

Guarda con `Ctrl+O`, confirma con `Enter` y sal con `Ctrl+X`.

Mantén `AUTO_SHUTDOWN=false` durante las pruebas.

## 5. Probar accesos sin mostrar secretos

```bash
sudo gcloud secrets versions access latest --secret=google-oauth-token-json >/dev/null && echo TOKEN_OK
sudo gcloud secrets versions access latest --secret=google-client-secret-json >/dev/null && echo CLIENTE_OK
sudo docker pull southamerica-west1-docker.pkg.dev/descarga-gmail-automatica/gmail-downloader/gmail-cloud-run:vm-v5
```

El resultado debe mostrar `TOKEN_OK`, `CLIENTE_OK` y finalizar la descarga de
la imagen.

## 6. Primera prueba controlada

Antes de iniciar, pausa temporalmente el activador de Cloud Scheduler del job
antiguo de Cloud Run para que no existan dos consumidores de Gmail.

Para volver a probar correos anteriores, elimina en Gmail las etiquetas
`Descarga-Automatica-Error` o `Descarga-Automatica-Manual` de esos mensajes y
déjalos como no leídos.

Inicia V5.1:

```bash
sudo systemctl start --no-block gmail-downloader.service
sudo journalctl -u gmail-downloader.service -f -o cat
```

Sal del seguimiento de registros con `Ctrl+C`; eso no detiene la aplicación.

## 7. Revisar el resultado

```bash
sudo systemctl status gmail-downloader.service --no-pager
sudo journalctl -u gmail-downloader.service -n 200 --no-pager
sudo ls -lah /var/lib/gmail-downloader/state/diagnostics
```

El registro debe comenzar con:

```text
VERSION_APP: V5.1-OVERLAY-AND-CHALLENGE-2026-07-31
```

## 8. Ejecutar cada 15 minutos mientras la VM permanece encendida

Solo después de aprobar la prueba manual:

```bash
sudo systemctl enable --now gmail-downloader.timer
systemctl list-timers gmail-downloader.timer
```

## 9. Modo de menor costo

Cuando V5 haya funcionado varios días:

1. Desactiva el temporizador local.
2. Activa el servicio para que se ejecute al arrancar.
3. Cambia `AUTO_SHUTDOWN=true`.
4. Configura Cloud Scheduler para encender la VM cada 15 minutos.

```bash
sudo systemctl disable --now gmail-downloader.timer
sudo systemctl enable gmail-downloader.service
sudo nano /etc/gmail-downloader/worker.env
```

En este modo, Cloud Scheduler enciende la VM, el servicio procesa Gmail y la VM
se apaga al terminar. Si una descarga tarda más de 15 minutos, una solicitud de
encendido adicional no crea una segunda máquina ni una segunda ejecución.

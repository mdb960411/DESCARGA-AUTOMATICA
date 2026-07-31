# Actualización V5.1: capas reales observadas en la VM

Esta revisión se basa en capturas generadas por el navegador dentro de la VM,
no en nuevos selectores supuestos.

## WeTransfer

La página mostraba el panel de privacidad sobre la transferencia. El enlace
comercial `Sé Ultimate` contenía una ruta relacionada con descargas y producía
un falso positivo. V5.1:

- rechaza o acepta el panel antes de buscar archivos;
- repite la limpieza de capas durante la carga dinámica;
- excluye acciones comerciales de la detección de descarga.

## TransferNow

El primer clic podía abrir publicidad superpuesta con el control `Close`. V5.1
cierra esa capa en la página principal o en sus marcos antes de continuar. Las
confirmaciones dirigidas al remitente, con asunto `Sus archivos se han enviado
con éxito`, se ignoran porque no son transferencias recibidas.

## SendAllFiles

La captura de la VM mostró una casilla explícita `Verifique que es un ser
humano` de Cloudflare. Eso es distinto de un botón de descarga cambiante. V5.1
lo clasifica como intervención humana y evita cinco reintentos idénticos. La
aplicación no intenta eludir ni resolver automáticamente esa validación.

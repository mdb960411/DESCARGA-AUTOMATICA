# Historial de cambios

## V4.1 — SendAllFiles multarchivo y estados precisos

- Espera de hasta 60 segundos para la carga dinámica de SendAllFiles.
- Detección y descarga de todos los archivos de una misma transferencia.
- Resultado multarchivo con soporte de estados parciales.
- Identificación explícita de enlaces caducados, no encontrados o protegidos.
- Eliminación de variantes repetidas del mismo envío de WeTransfer.
- Nueva etiqueta Gmail `Descarga-Automatica-Ignorado`.
- Los correos sin archivos dejan de contarse como errores y permanecen no leídos.
- Cierre ordenado de Playwright sin callbacks de rutas pendientes.
- Nueva firma de log `V4.1-MULTIFILE-2026-07-23`.

## V4 — Archivos gráficos grandes

- Volumen externo compatible con Cloud Storage FUSE.
- Descarga HTTP por bloques y límite de tamaño configurable.
- Transferencia del navegador a HTTP para reducir memoria.
- Directorio de descarga de Chromium configurable dentro del volumen.
- Subida reanudable a Drive con progreso y reintentos.
- Identificación de archivos ya subidos por correo para evitar duplicados.
- Estados de Gmail procesado, parcial y error.
- Exclusión de mensajes con error para evitar ciclos infinitos.
- Limpieza por mensaje y por ejecución.
- Extensiones predeterminadas para industria gráfica.
- Protección de tokens de transferencia en Cloud Logging.
- Validación temprana de escritura sobre el volumen.

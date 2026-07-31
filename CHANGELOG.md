# Historial de cambios

## V4.5.5 — Navegador visible sobre pantalla virtual

- WeTransfer y SendAllFiles usan Chromium visible dentro de Xvfb en Cloud Run.
- El Dockerfile instala y activa `xvfb` y `xauth` antes de iniciar la app.
- Las sesiones sin panel descargable se reemplazan después de 30 segundos.
- WeTransfer conserva cinco etapas inteligentes, pero limita cada sesión a
  100 segundos.
- Nueva firma `V4.5.5-VIRTUAL-DISPLAY-2026-07-31`.

## V4.5.4 — Reintento automático de SendAllFiles

- Una validación temporalmente pendiente de Cloudflare deja de clasificarse
  inmediatamente como descarga manual.
- SendAllFiles realiza hasta tres intentos aislados con navegadores nuevos.
- Si Turnstile todavía no termina, el mensaje conserva un estado de reintento
  automático para futuras ejecuciones.
- Nueva variable `SENDALLFILES_DOWNLOAD_ATTEMPTS`, con valor predeterminado
  `3`.
- Nueva firma `V4.5.4-SENDALLFILES-AUTO-RETRY-2026-07-30`.

## V4.5.3 — Panel y descarga multipaso de WeTransfer

- WeTransfer usa el perfil compatible completo para que su aplicación dinámica
  pueda cargar el panel lateral de la transferencia.
- La espera del panel aumenta de 45 a 75 segundos.
- El navegador inteligente admite hasta cinco etapas y reconoce el control
  `Ir a la transferencia`.
- Después de cada avance espera la carga del siguiente control en vez de
  finalizar inmediatamente.
- Una descarga iniciada de forma asíncrona se conserva aunque el evento ocurra
  después de la ventana inmediata del clic.
- Se mantienen las exclusiones de publicidad como `Sé Ultimate`.
- Nueva firma `V4.5.3-WETRANSFER-MULTISTEP-2026-07-30`.

## V4.5.2 — Reintentos internos de TransferNow

- TransferNow realiza hasta tres intentos aislados con navegadores nuevos
  cuando abre una segunda etapa pero el archivo no comienza.
- Los enlaces caducados, no disponibles o protegidos por contraseña siguen
  sin repetirse innecesariamente.
- Nueva variable `TRANSFERNOW_DOWNLOAD_ATTEMPTS`, con valor predeterminado `3`.
- Nueva firma `V4.5.2-TRANSFERNOW-RETRY-2026-07-30`.

## V4.5.1 — Control real de WeTransfer

- La espera inicial de WeTransfer ignora los enlaces publicitarios y aguarda
  hasta 45 segundos el control verdadero de descarga.
- `Sé Ultimate`, planes, precios y promociones quedan excluidos tanto de los
  selectores directos como del navegador inteligente.
- Nueva firma `V4.5.1-WETRANSFER-CONTROL-2026-07-30`.

## V4.5 — Reintentos, idempotencia y ejecución programada

- WeTransfer realiza hasta tres intentos aislados con navegadores nuevos ante
  fallos transitorios de su interfaz.
- Los errores técnicos se reintentan en ejecuciones posteriores antes de
  etiquetar definitivamente el mensaje como error.
- Nuevas etiquetas automáticas
  `Descarga-Automatica-Reintento-1` y
  `Descarga-Automatica-Reintento-2`.
- Drive reconoce la misma transferencia aunque llegue con otro ID de correo.
- Compatibilidad con archivos de V4.4 mediante comparación segura de nombre,
  tamaño y MD5.
- Verificación posterior de las etiquetas aplicadas por Gmail.
- Confirmaciones de envío de TransferNow ignoradas automáticamente.
- Bloqueo persistente para evitar ejecuciones superpuestas de Cloud Scheduler.
- Nueva firma `V4.5-RETRY-IDEMPOTENCY-2026-07-29`.

## V4.4 — Protección contra falsos archivos

- Los recursos incrustados del HTML ya no se interpretan como enlaces
  descargables.
- Los correos ajenos a transferencias, como alertas de seguridad, se etiquetan
  como ignorados si no contienen adjuntos o enlaces directos verificables.
- El respaldo de captura de red exige evidencia fuerte: adjunto HTTP, MIME de
  archivo o flujo binario con extensión válida.
- Se bloquean respuestas de analítica, publicidad, cookies, logos, píxeles e
  iconos.
- La captura de red elige la evidencia más fuerte en vez de la última respuesta
  observada.
- WeTransfer acepta la pantalla intermedia de condiciones cuando aparece.
- WeTransfer conserva la descarga nativa en el bucket para evitar que una URL
  de un solo uso quede inválida al cancelar Chromium.
- Las variantes alternativas de un mismo correo de WeTransfer se prueban como
  respaldo; un enlace fallido no deja el mensaje parcial si otra variante
  completa correctamente el archivo.
- TransferNow puede continuar en una pestaña o etapa nueva después del primer
  clic.
- Smart Browser descarta contenedores no interactivos y resultados
  publicitarios.
- Nueva firma `V4.4-FALSE-POSITIVE-GUARD-2026-07-29`.

## V4.3 — Recuperación de proveedores y atención manual

- Nueva etiqueta Gmail `Descarga-Automatica-Manual`.
- SendAllFiles pasa a estado `MANUAL` cuando Cloudflare Turnstile queda
  pendiente; ya no se registra como enlace caducado ni se reintenta
  indefinidamente.
- WeTransfer, TransferNow y SwissTransfer usan User-Agent nativo de Chromium.
- Búsqueda de controles en la página principal y en todos sus marcos.
- Smart Browser de hasta tres etapas para interfaces donde un primer botón
  abre la pantalla de descarga definitiva.
- Reconocimiento por texto, atributos accesibles, `data-testid`, título y
  destino del control.
- Captura de respuestas de archivo en la red como respaldo del evento de
  descarga del navegador.
- Diagnóstico seguro de acciones visibles, sin publicar enlaces privados.
- Resumen final con estado global y contadores separados de errores y acciones
  manuales.
- Nueva firma `V4.3-PROVIDER-RECOVERY-2026-07-28`.

## V4.2 — Compatibilidad reforzada con SendAllFiles

- User-Agent nativo de Chromium para SendAllFiles.
- Service Workers habilitados únicamente para ese proveedor.
- Perfil con menos restricciones de red para su aplicación dinámica.
- Búsqueda de botones de descarga en todos los marcos de la página.
- Selectores exactos y accesibles adicionales.
- Descarga nativa sobre el volumen montado para conservar la sesión de
  Cloudflare.
- Captura de solicitudes originadas por Service Workers.
- User-Agent real conservado en transferencias HTTP del resto de proveedores.
- Diagnóstico seguro de marcos, controles visibles, Service Workers y
  Turnstile.
- Nueva firma `V4.2-SENDALLFILES-COMPAT-2026-07-24`.

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

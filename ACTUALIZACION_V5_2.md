# Actualización V5.2: acciones seguras basadas en capturas reales

Esta versión responde al diagnóstico realizado en la VM el 3 de agosto de
2026. La ejecución procesó correctamente dos transferencias de TransferNow y
un adjunto de Gmail, pero dejó cuatro WeTransfer y una transferencia múltiple
de TransferNow en reintento.

## WeTransfer

Las capturas demostraron que Smart Browser interpretaba el enlace comercial
`Sé Ultimate` como una descarga porque su destino incluía la palabra
`downloads`. Ese clic llevaba a `Crea tu cuenta` y hacía imposible encontrar el
archivo.

V5.2 centraliza una política de acciones bloqueadas que se aplica a los
selectores normales y al navegador inteligente. Se bloquean:

- `Sé Ultimate` y variantes comerciales;
- registro, inicio de sesión, precios, planes y actualización de cuenta;
- publicidad y destinos ajenos al proveedor.

Además, Smart Browser se detiene sin hacer clic cuando la página ya corresponde
a registro o cuenta. Los enlaces antiguos que hayan vencido no pueden
recuperarse; la validación definitiva debe realizarse con una transferencia
nueva y vigente.

## TransferNow

La captura mostró seis archivos y un enlace azul `<a>` con el texto
`Download all`. La versión anterior probaba primero iconos individuales y podía
agotar los 120 segundos antes de llegar a ese control.

V5.2 prueba primero `Download all`/`Descargar todo` como enlace, luego los
botones y finalmente los iconos individuales. Cada control dispone de hasta
ocho segundos y siempre se reservan veinticinco segundos para Smart Browser.

## SendAllFiles

La captura vuelve a mostrar una casilla explícita `Verifique que es un ser
humano` de Cloudflare. V5.2 mantiene la clasificación manual: no intenta
eludir esa verificación.

## Validación

- Compilación de todos los módulos Python.
- 32 pruebas automáticas, incluidas regresiones para `Sé Ultimate`, rutas de
  registro y prioridad de `Download all`.
- Sin cambios en secretos, tokens, permisos de Google ni estructura de la VM.

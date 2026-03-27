# Modulo Inventario Backend

## Rol del modulo

`inventario` es el responsable del stock real del ERP. No es un catalogo ni un CRUD de existencias: concentra la integridad operativa del stock, la valorizacion, la trazabilidad y los documentos de ajuste o traslado.

## Responsabilidades principales

### Stock operativo

- Mantiene stock por producto y bodega.
- Mantiene `valor_stock` y usa `costo_promedio` del producto como base operativa.
- Impide mutacion directa de existencias por API; el stock se modifica solo via servicios.

### Trazabilidad

- Registra movimientos valorizados en `MovimientoInventario`.
- Mantiene `InventorySnapshot` para lectura historica y conciliacion.
- Mantiene trazabilidad por `StockLote` y `StockSerie`.
- Audita movimientos, reservas, liberaciones y documentos masivos.

### Operacion documental

- Soporta ajuste simple y traslado simple.
- Soporta ajustes masivos y traslados masivos con:
  - borrador
  - confirmacion posterior
  - duplicado
  - eliminacion de borradores
  - importacion CSV/XLSX
  - edicion posterior del borrador

### Correcciones administrativas

- Permite correccion de codigo de lote con auditoria.
- Permite anular lotes vacios y sin series disponibles.
- Bloquea lotes “muy similares” para evitar duplicados por digitacion como `1` vs `001`.

## Integraciones backend

### Productos

- Consume configuracion de `maneja_inventario`, fraccionamiento, lotes, series y vencimiento.
- Usa `precio_costo` y `costo_promedio` como referencia operativa.
- No delega al modulo `productos` la mutacion de stock.

### Compras y ventas

- Reciben o consumen stock via movimientos documentales.
- No deben alterar `StockProducto` directo.

### Auditoria e integraciones

- Usa `DomainEventService.record_event()` en cambios funcionales.
- Usa `OutboxService.enqueue()` para consumidores externos.
- Usa `AuditoriaService.registrar_evento()` en flujos sensibles.

## Servicios principales

- `inventario_service.py`
  Nucleo del dominio: movimientos, reservas, liberaciones, regularizaciones, traslados y kardex.
- `documento_inventario_service.py`
  Documentos masivos de ajuste y traslado.
- `bulk_import_service.py`
  Importacion masiva CSV/XLSX con `dry_run`.
- `bodega_service.py`
  Alta, actualizacion e inactivacion controlada de bodegas.
- `lote_service.py`
  Correccion y anulacion segura de lotes.

## Contratos funcionales clave

### Integridad del stock

- `stocks` es de solo lectura por API.
- Todo cambio de existencia pasa por servicios del dominio.
- Los errores de negocio se exponen como `AppError`.

### Lotes, vencimiento y series

- Un producto con lotes o vencimiento no debe ajustarse “a ciegas”.
- Si un lote existente ya tiene vencimiento, no puede recibir otro distinto.
- Las series se crean solo en entrada y deben existir para salida.
- La importacion masiva valida lotes, vencimiento y similitud de codigos antes de crear borradores.

### Documentos masivos

- La importacion nunca mueve stock directo; crea borradores.
- Confirmar documento ejecuta los movimientos reales.
- Los borradores pueden editarse, duplicarse o eliminarse mientras sigan en `BORRADOR`.

### Correccion de lotes

- Corregir un lote renombra o fusiona stock y series preservando trazabilidad.
- Anular un lote solo se permite cuando no tiene stock ni series disponibles.

## Reportes y lectura operacional

- `analytics` entrega resumen valorizado por producto o bodega.
- `reconciliation` entrega dataset paginado de diferencias contra snapshots.
- `historial` y `auditoria` exponen trazabilidad de movimientos.
- `kardex` concentra lectura transaccional por producto y bodega.

## Estado actual del modulo

El modulo ya cumple un nivel enterprise solido en estos puntos:

- integridad de stock blindada
- documentos simples y masivos
- importacion con borrador
- auditoria y outbox
- trazabilidad por lote, vencimiento y serie
- conciliacion y reportes operativos
- correccion administrativa de lotes

## Deuda residual baja

- separar permisos finos por operacion especializada cuando el negocio lo necesite
- seguir ampliando documentacion de integraciones cruzadas si crecen ventas o compras

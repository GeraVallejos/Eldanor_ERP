# Modulo Productos Backend

## Rol del modulo

`productos` es el maestro transversal del ERP para catalogo, pricing comercial y configuracion operativa de inventario.

No debe entenderse como un CRUD aislado. En backend concentra reglas de negocio sobre:

- catalogo maestro de productos y servicios
- categorias e impuestos
- listas de precio y resolucion de precio comercial
- trazabilidad, gobernanza e historial del maestro
- snapshots y versionado funcional del producto
- importacion masiva controlada

## Responsabilidades principales

### Maestro comercial

- Mantiene `precio_referencia` como respaldo comercial base.
- Resuelve precio vigente via `PrecioComercialService`.
- Prioriza lista especifica de cliente, luego lista general vigente y finalmente `precio_referencia`.

### Maestro operativo

- Define configuracion que otros modulos consumen:
  - `maneja_inventario`
  - `permite_decimales`
  - `usa_lotes`
  - `usa_series`
  - `usa_vencimiento`
  - `precio_costo` y `costo_promedio` como referencia operativa

### Salud del maestro

- Expone trazabilidad documental del producto.
- Expone gobernanza del maestro para detectar brechas de configuracion.
- Mantiene snapshots versionados para comparar y restaurar configuraciones historicas.

## Integraciones backend

### Ventas

- Consume `Producto` como maestro del item comercial.
- Debe resolver pricing via el endpoint o servicio de precio del modulo.
- No debe depender de `precio_referencia` como unica regla cuando exista pricing comercial vigente.

### Compras

- Usa `Producto` como maestro catalografico y de trazabilidad historica.
- Los documentos de compra alimentan uso historico del producto.
- El precio de compra no define el precio comercial de ventas.

### Inventario

- Consume configuracion del producto para fraccionamiento, lotes, series y vencimiento.
- Usa `precio_costo` y `costo_promedio` para valorizacion operativa.
- `productos` no modifica stock directo; inventario es el responsable del stock real.

## Servicios principales

- `producto_service.py`
  Alta, actualizacion y baja logica del maestro.
- `precio_service.py`
  Resolucion de precio comercial vigente.
- `lista_precio_service.py`
  Administracion de listas e items comerciales.
- `producto_trazabilidad_service.py`
  Resumen historico de uso documental del producto.
- `producto_gobernanza_service.py`
  Evaluacion de readiness y salud del maestro.
- `producto_snapshot_service.py`
  Versionado, comparacion y restauracion de snapshots.
- `bulk_import_service.py`
  Importacion masiva de productos.
- `lista_precio_bulk_import_service.py`
  Importacion masiva de items de listas de precio.

## Contratos funcionales clave

### Precio comercial

- El precio comercial se resuelve con jerarquia de listas y fallback final en `precio_referencia`.
- Si una lista de cliente no contiene item para el producto, debe probarse lista general vigente antes de caer al respaldo base.

### Trazabilidad del maestro

- Solo debe contar documentos operativos validos.
- Borradores y anulados no deben inflar uso ni penalizar gobernanza.

### Gobernanza del maestro

- Evalua si el producto esta listo para operar sin tomar como uso real documentos no vigentes.
- Debe reflejar brechas del maestro, no ruido documental.

### Versionado

- El snapshot del producto debe tolerar concurrencia mediante lock y reintento.
- Restaurar version debe preservar trazabilidad funcional.

## Eventos y trazabilidad

El modulo emite eventos funcionales y de integracion en flujos relevantes, especialmente en:

- creacion y actualizacion de producto
- cambios de catalogos auxiliares
- alta, actualizacion y eliminacion de listas de precio
- importaciones masivas de productos y listas

Patron esperado:

- `DomainEventService.record_event()` para trazabilidad funcional
- `OutboxService.enqueue()` para consumidores externos

## Criterio de readiness del maestro

### Producto listo para vender

Se considera listo para vender cuando, como minimo:

- esta activo
- tiene SKU y nombre consistentes
- tiene configuracion tributaria valida cuando aplica
- puede resolver precio comercial via lista o `precio_referencia`

### Producto listo para inventario

Se considera listo para inventario cuando, como minimo:

- `maneja_inventario` refleja correctamente su naturaleza
- reglas de fraccionamiento son consistentes
- reglas de lote, serie y vencimiento son coherentes entre si
- tiene costo base operativo razonable para valorizacion inicial

### Producto observado por gobernanza

Debe quedar observado cuando presenta brechas reales del maestro, por ejemplo:

- configuracion tributaria faltante
- pricing comercial insuficiente para su uso real
- inconsistencias entre configuracion del producto y su comportamiento esperado

## Estado actual del modulo

El modulo ya cumple de forma razonable el estandar enterprise del ERP en estos puntos:

- reglas de negocio centralizadas en servicios
- contrato de errores consistente
- pricing comercial con jerarquia real
- integracion explicita con ventas, compras e inventario
- trazabilidad y gobernanza del maestro
- snapshots y restauracion versionada
- cobertura funcional relevante en tests

## Deuda residual baja

La deuda restante es de consolidacion, no de rescate arquitectonico:

- ampliar documentacion de contratos si aparecen nuevos consumidores
- seguir fortaleciendo tests de integracion cruzada cuando crezcan ventas o inventario
- mantener alineado frontend y backend cuando se agreguen nuevos flujos comerciales

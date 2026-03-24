# Modulo Productos

`productos` actua como maestro comercial y operativo del ERP. No es solo un CRUD de catalogo: concentra definicion del producto, pricing base, listas de precio, analisis de gobernanza del maestro y puntos de integracion con ventas, compras e inventario.

## Responsabilidad funcional

- Mantener el maestro de productos y servicios.
- Gestionar catalogos auxiliares como categorias e impuestos.
- Resolver y administrar listas de precio comerciales.
- Exponer salud del maestro mediante trazabilidad, historial, gobernanza y versionado.
- Servir como fuente transversal para ventas, compras e inventario.

## Estructura frontend

```text
src/modules/productos/
  pages/
    ProductosListPage.jsx
    ProductosCreatePage.jsx
    ProductosDetailPage.jsx
    ProductosAnalisisPage.jsx
    ProductosListasPrecioPage.jsx
    ProductosListaPrecioDetailPage.jsx
  services/
    productosCatalogCache.js
  store/
    api.js
    hooks.js
    mutations.js
  tests/
```

## Capas principales

- `store/api.js`
  Centraliza endpoints y helpers CRUD/paginacion del modulo.
- `store/hooks.js`
  Encapsula cargas de lectura y estado de vistas principales.
- `store/mutations.js`
  Encapsula mutaciones UI con validacion local de permisos, toasts y refresh.
- `services/productosCatalogCache.js`
  Cache compartido para busqueda ligera de productos en flujos comerciales.

## Criterio de estado

El modulo usa un enfoque mixto y deliberado:

- `productosSlice`
  Para estado compartido y transversal del catalogo principal.
  Incluye listado de productos y catalogos base reutilizados como categorias e impuestos.
- `store/hooks.js`
  Para cargas acopladas a pantallas o vistas de lectura que no necesitan quedar globales.
  Ejemplos: detalle, analisis, cabecera de lista de precio, formulario de edicion.
- `store/mutations.js`
  Para mutaciones de UI con permisos locales, toasts y refresh post-operacion.

Regla operativa:

- Si varias pantallas consumen el mismo recurso de forma persistente, preferir `slice`.
- Si el estado pertenece a una sola vista o flujo, preferir `hook`.
- Evitar que el mismo recurso tenga una fuente de verdad duplicada en `slice` y `hook` al mismo tiempo.

## Integraciones clave

- Ventas
  Usa el maestro para pedidos, pricing y readiness comercial.
  Los formularios comerciales deben resolver precio via `/productos/{id}/precio/` cuando exista cliente/fecha, con fallback silencioso a `precio_referencia` solo como respaldo UX.
- Compras
  Usa el producto para documentos de proveedor y trazabilidad historica.
  El precio de compra puede nacer del proveedor, OC o documento asociado; `precio_referencia` del maestro actua solo como sugerencia inicial y no como regla comercial obligatoria.
- Inventario
  Administra stock real y costo promedio; el maestro solo los expone como referencia.
  La valorizacion operativa usa `costo_promedio` y `precio_costo`, no `precio_referencia`, preservando la separacion entre maestro comercial y stock real.
- Auditoria/versionado
  El detalle y analisis del producto consumen historial, snapshots y gobernanza.

## Contratos operativos

- Pricing comercial
  `productos` resuelve el precio vigente con jerarquia de listas especificas, listas generales y respaldo final en `precio_referencia`.
- Trazabilidad del maestro
  Solo considera documentos operativos validos; borradores y anulados no deben penalizar gobernanza ni inflar uso historico.
- Compras
  Alimenta historial de abastecimiento y trazabilidad del producto, pero no define el precio comercial de venta.
- Inventario
  Consume configuracion del producto para lotes, series, vencimiento, fraccionamiento y costo base; el modulo `productos` no modifica stock directamente.

## Decisiones actuales

- El frontend muestra el maestro y sus vistas analiticas, pero no modifica stock operativo desde `productos`.
- Las mutaciones de UI validan permisos antes de intentar llamadas backend.
- Los errores backend se muestran usando el contrato `detail` + `errorCode` cuando aplica.
- Las listas de precio y la busqueda de productos reutilizan capa comun en vez de pegarle directo a la API desde cada pagina.

## Criterio de readiness del modulo

- Listo para operar como modulo enterprise razonable
  - pricing comercial centralizado
  - permisos y errores UI consistentes
  - integraciones explicitas con ventas, compras e inventario
  - documentacion frontend y backend del modulo
- Deuda residual baja
  - seguir ampliando tests de integracion si otros modulos agregan nuevos contratos
  - mantener el criterio `slice vs hooks` estable cuando el modulo siga creciendo

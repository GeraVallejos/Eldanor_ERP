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

## Integraciones clave

- Ventas
  Usa el maestro para pedidos, pricing y readiness comercial.
- Compras
  Usa el producto para documentos de proveedor y trazabilidad historica.
- Inventario
  Administra stock real y costo promedio; el maestro solo los expone como referencia.
- Auditoria/versionado
  El detalle y analisis del producto consumen historial, snapshots y gobernanza.

## Decisiones actuales

- El frontend muestra el maestro y sus vistas analiticas, pero no modifica stock operativo desde `productos`.
- Las mutaciones de UI validan permisos antes de intentar llamadas backend.
- Los errores backend se muestran usando el contrato `detail` + `errorCode` cuando aplica.
- Las listas de precio y la busqueda de productos reutilizan capa comun en vez de pegarle directo a la API desde cada pagina.

## Deuda residual recomendada

- Unificar de forma definitiva el criterio de estado entre slice Redux y hooks locales.
- Aumentar cobertura de tests sobre permisos UI, errores de negocio y flujos de edicion.
- Seguir estandarizando hooks CRUD especificos por recurso si el modulo sigue creciendo.

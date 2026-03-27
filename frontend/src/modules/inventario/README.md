# Modulo Inventario Frontend

`inventario` concentra la operacion diaria de stock y la trazabilidad avanzada del modulo. El objetivo UI no es mezclar todo en una sola pantalla, sino separar operacion comun de analisis especialista.

## Responsabilidad funcional

- Operar ajustes y traslados simples.
- Gestionar documentos masivos con borrador, importacion y confirmacion.
- Exponer `Kardex`, `Reportes` y auditoria contextual.
- Permitir correccion avanzada de lotes desde `Reportes`, con acceso contextual desde `Kardex`.

## Estructura frontend

```text
src/modules/inventario/
  pages/
    InventarioBodegasPage.jsx
    InventarioAjustesPage.jsx
    InventarioTrasladosPage.jsx
    InventarioKardexPage.jsx
    InventarioReportesPage.jsx
    InventarioAuditoriaPage.jsx
    InventarioAjustesMasivosPage.jsx
    InventarioAjustesMasivosDetailPage.jsx
    InventarioTrasladosMasivosPage.jsx
    InventarioTrasladosMasivosDetailPage.jsx
  store/
    api.js
    hooks.js
  tests/
```

## Criterio UX actual

### Flujos operativos comunes

- `Ajustes`
  Correccion puntual por producto.
- `Traslados`
  Movimiento puntual entre bodegas.
- `Bodegas`
  Maestro operativo de bodegas con alta, edicion e inactivacion.

### Flujos avanzados

- `Kardex`
  Trazabilidad transaccional por producto y bodega, con auditoria del movimiento.
- `Reportes`
  Resumen valorizado, conciliacion, remediacion, correccion de lotes, cortes globales, cierres mensuales y exportacion de snapshots historicos.
- `Auditoria`
  Ruta avanzada para usuario especialista; no compite con la navegacion operativa comun.

### Documentos masivos

- Ajustes y traslados masivos usan grilla tipo hoja de calculo.
- El importador crea borradores, nunca movimientos finales.
- El detalle del documento sirve para revisar, exportar, duplicar, eliminar o confirmar.

## Capas principales

- `store/api.js`
  Endpoints, paginacion y acciones de detalle del modulo.
- `store/hooks.js`
  Lecturas reutilizables para historial y auditoria.
- `pages/*.jsx`
  Flujos operativos y analiticos del modulo.

## Decisiones UI relevantes

- La auditoria avanzada no esta en cada formulario para no sobrecargar al usuario comun.
- Los errores de negocio se muestran inline con mensaje util, sin exponer codigos tecnicos.
- `Reportes` concentra la lectura avanzada y la remediacion.
- `Reportes` tambien concentra los cortes globales y cierres mensuales del inventario para consulta historica por fecha de cierre.
- La seccion de cortes en `Reportes` es desplegable para no saturar la pantalla principal.
- `Kardex` puede derivar a `Reportes` para corregir lotes de un movimiento con contexto precargado.

## Contratos operativos

- `Ajustes` soporta lote y vencimiento cuando el producto lo requiere.
- `Ajustes masivos` soportan lote y vencimiento por linea.
- `Reportes` exporta el dataset completo filtrado.
- `Reportes` muestra lotes activos, proximo vencimiento y series disponibles.
- `Reportes` permite generar cortes globales y revisar su detalle completo por producto y bodega.
- `Reportes` permite generar cierres mensuales contables sin duplicar el mismo periodo.
- `Reportes` permite exportar el corte o cierre seleccionado en Excel y PDF.
- La correccion de lotes se hace desde `Reportes`, no desde formularios operativos simples.

## Estado actual del modulo

El frontend ya se considera en estado enterprise razonable:

- operacion comun separada de flujos avanzados
- documentos masivos con borrador e importacion
- reportes valorizados y conciliacion
- cortes y cierres historicos exportables desde `Reportes`
- trazabilidad contextual en `Kardex`
- correccion administrativa de lotes accesible sin crear una pagina aparte

## Deuda residual baja

- seguir fortaleciendo pruebas frontend cuando el entorno permita ejecutar Vitest de forma estable
- ajustar permisos especializados por pantalla cuando el negocio los formalice

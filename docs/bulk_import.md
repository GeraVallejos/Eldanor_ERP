# Carga Masiva (CSV/XLSX)

## Objetivo
Permitir carga masiva de datos con reglas consistentes del ERP, control estricto de seguridad y una experiencia uniforme para usuario y frontend.

## Seguridad y consistencia
- Solo rol `ADMIN` de la empresa (o superuser) puede ejecutar carga masiva.
- Archivo permitido: `.csv` y `.xlsx`.
- Tamano maximo: 2 MB.
- Maximo por archivo: 2000 filas.
- Codificacion requerida: UTF-8 para CSV.
- XLSX se procesa con `openpyxl` en modo lectura eficiente (`read_only=True`).
- Cada fila debe validarse con la misma logica funcional del flujo real.
- La previsualizacion debe usar `dry_run` real: ejecuta validaciones y reglas completas, pero sin persistir cambios.
- Los errores por fila deben devolverse en formato legible para usuario final, no como estructuras tecnicas crudas.
- El resultado debe devolver un contrato estandar para trazabilidad y reutilizacion en frontend.

## Estandar ERP obligatorio

Toda nueva importacion masiva del ERP debe cumplir estas reglas:

1. Exponer `POST .../bulk_import/` y `GET .../bulk_template/`.
2. Aceptar `multipart/form-data` con campo `file`.
3. Soportar `dry_run=true` en el mismo endpoint de importacion.
4. En `dry_run`, ejecutar la misma logica funcional que la importacion real dentro de una transaccion con rollback.
5. Devolver el mismo contrato de respuesta tanto en preview como en ejecucion real.
6. Emitir auditoria, domain events y outbox solo en la ejecucion real, no en `dry_run`.
7. Formatear errores por fila con mensajes legibles y consistentes.
8. Tener test API que pruebe que `dry_run` no persiste cambios.

## Contrato de respuesta estandar

Toda importacion masiva debe responder con este formato:

```json
{
  "created": 10,
  "updated": 4,
  "errors": [
    { "line": 6, "detail": "El SKU es obligatorio." }
  ],
  "warnings": [],
  "total_rows": 15,
  "successful_rows": 14,
  "dry_run": false
}
```

Notas:
- `errors` siempre es lista de errores por fila.
- `warnings` siempre es lista, aunque venga vacia.
- `successful_rows` debe ser `created + updated`.
- `dry_run` indica si la respuesta corresponde a previsualizacion.

## Utilidades compartidas backend

Para evitar duplicacion, los servicios deben reutilizar `apps.core.services.bulk_import`:

- `bulk_import_execution_context(dry_run=...)`
  Ejecuta el preview dentro de una transaccion con rollback automatico.
- `build_bulk_import_result(...)`
  Construye el payload de respuesta con el contrato estandar.
- `format_bulk_import_row_error(exc)`
  Convierte errores complejos en mensajes legibles para la UI.

Esto deja el comportamiento alineado entre productos, listas de precio, contactos, facturacion y tesoreria.

## Endpoints
Carga masiva:
- `POST /api/productos/bulk_import/`
- `POST /api/clientes/bulk_import/`
- `POST /api/proveedores/bulk_import/`
- `POST /api/listas-precio/{id}/bulk_import/`
- `POST /api/rangos-folios-tributarios/bulk_import/`
- `POST /api/movimientos-bancarios/bulk_import/`

Plantillas XLSX:
- `GET /api/productos/bulk_template/`
- `GET /api/clientes/bulk_template/`
- `GET /api/proveedores/bulk_template/`
- `GET /api/listas-precio/{id}/bulk_template/`
- `GET /api/rangos-folios-tributarios/bulk_template/`
- `GET /api/movimientos-bancarios/bulk_template/`

Formato: `multipart/form-data` con campo `file` para cargas.

Preview:
- El mismo endpoint `POST .../bulk_import/` acepta `dry_run=true`.

## Columnas recomendadas
### Productos
Obligatorias:
- `nombre`
- `sku`

Valores criticos:
- `tipo`: solo `PRODUCTO` o `SERVICIO`

Opcionales:
- `tipo` (`PRODUCTO` o `SERVICIO`)
- `descripcion`
- `categoria` (nombre exacto existente)
- `impuesto` (nombre exacto existente)
- `precio_referencia`
- `precio_costo`
- `maneja_inventario`
- `stock_minimo`
- `activo`

Notas:
- `stock_actual` no debe importarse desde la plantilla de productos.
- `precio_costo` solo debe aplicarse al crear productos nuevos; no debe corregir costos de productos existentes por carga masiva.

### Clientes
Obligatorias:
- `nombre`

Valores criticos:
- `tipo`: solo `EMPRESA` o `PERSONA`

Opcionales:
- `rut`
- `email`
- `tipo` (`EMPRESA` o `PERSONA`)
- `razon_social`
- `telefono`
- `celular`
- `notas`
- `activo`
- `limite_credito`
- `dias_credito`
- `categoria_cliente`
- `segmento`

### Proveedores
Obligatorias:
- `nombre`

Valores criticos:
- `tipo`: solo `EMPRESA` o `PERSONA`

Opcionales:
- `rut`
- `email`
- `tipo` (`EMPRESA` o `PERSONA`)
- `razon_social`
- `telefono`
- `celular`
- `notas`
- `activo`
- `giro`
- `vendedor_contacto`
- `dias_credito`

### Listas de precio
Obligatorias:
- `sku`
- `precio`

Opcionales:
- `descuento_maximo`

Notas:
- La importacion es por lista existente.
- Si el item ya existe para la combinacion `lista + producto`, se actualiza.
- Puede devolver advertencias no bloqueantes, por ejemplo precio igual a `0`.

## UX esperada en frontend

Todo flujo de carga masiva debe seguir este patron:

1. Descargar plantilla.
2. Seleccionar archivo.
3. Ejecutar preview con `dry_run=true`.
4. Mostrar resumen de `created`, `updated`, `errors`, `warnings` y muestra corta de filas problemáticas.
5. Confirmar importacion real solo si el usuario acepta.

El componente base recomendado es `BulkImportButton` en frontend.

## Testing minimo obligatorio

Cada importacion nueva debe incluir como minimo:

- test API de importacion exitosa
- test API de permisos
- test API de `dry_run` sin persistencia
- test de error por fila legible
- test de auditoria/eventos en la importacion real cuando aplique

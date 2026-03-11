# Carga Masiva (CSV/XLSX)

## Objetivo
Permitir carga masiva de productos, clientes y proveedores con reglas consistentes del ERP y control estricto de seguridad.

## Seguridad y consistencia
- Solo rol `ADMIN` de la empresa (o superuser) puede ejecutar carga masiva.
- Archivo permitido: `.csv` y `.xlsx`.
- Tamano maximo: 2 MB.
- Maximo por archivo: 2000 filas.
- Codificacion requerida: UTF-8 para CSV.
- XLSX se procesa con `openpyxl` en modo lectura eficiente (`read_only=True`).
- Cada fila se valida con las mismas reglas de negocio del modelo (save/full_clean).
- Resultado devuelve resumen y errores por fila para trazabilidad.

## Endpoints
Carga masiva:
- `POST /api/productos/bulk_import/`
- `POST /api/clientes/bulk_import/`
- `POST /api/proveedores/bulk_import/`

Plantillas XLSX:
- `GET /api/productos/bulk_template/`
- `GET /api/clientes/bulk_template/`
- `GET /api/proveedores/bulk_template/`

Formato: `multipart/form-data` con campo `file` para cargas.

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
- `stock_actual`
- `activo`

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

## Respuesta
```json
{
  "created": 10,
  "updated": 4,
  "errors": [
    { "line": 6, "detail": "El SKU es obligatorio." }
  ],
  "total_rows": 15,
  "successful_rows": 14
}
```

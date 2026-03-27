# Modulo Contactos Backend

## Rol del modulo

`contactos` es el maestro de terceros del ERP. Centraliza la identidad base del tercero y sus derivaciones funcionales como `cliente` y `proveedor`.

## Responsabilidades principales

- Mantener `Contacto` como agregado base del tercero.
- Gestionar roles derivados:
  - `Cliente`
  - `Proveedor`
- Mantener subrecursos asociados:
  - `Direccion`
  - `CuentaBancaria`
- Exponer auditoria consolidada del tercero.
- Soportar importacion masiva de clientes y proveedores.

## Integraciones backend

### Ventas

- Consume `Cliente` como contraparte comercial.
- Debe leer condiciones de credito y datos comerciales desde este modulo.

### Compras

- Consume `Proveedor` como contraparte de abastecimiento.
- Debe leer cuentas bancarias y datos tributarios desde este modulo.

### Auditoria

- El detalle del tercero agrega eventos de `CONTACTO`, `CLIENTE`, `PROVEEDOR`, `DIRECCION` y `CUENTA_BANCARIA`.

## Servicios principales

- `contacto_service.py`
  Nucleo del maestro de terceros y subrecursos.
- `bulk_import_service.py`
  Importacion masiva de clientes y proveedores.

## Contratos funcionales clave

- El RUT actua como llave de reutilizacion dentro de la empresa cuando corresponde.
- Crear un contacto con RUT ya existente puede reutilizar o reactivar el agregado existente.
- `include_inactive` solo debe ser visible para roles autorizados.
- Las validaciones tecnicas se traducen a `AppError`.

## Estado actual del modulo

El modulo ya esta bastante maduro en:

- maestro de terceros con servicios transaccionales
- auditoria del agregado y sus subrecursos
- importacion masiva
- soporte de clientes y proveedores como roles funcionales

## Deuda residual baja

- seguir ampliando documentacion de contratos cruzados si ventas o compras agregan nuevos consumidores

# Modulo Contactos Frontend

`contactos` concentra la UI del maestro de terceros del ERP. No es solo una lista de clientes: separa la vista general del tercero, los listados especializados de clientes o proveedores y el detalle consolidado del contacto.

## Responsabilidad funcional

- Gestionar contactos base.
- Gestionar altas y edicion de clientes.
- Gestionar altas y edicion de proveedores.
- Mostrar detalle del tercero con resumen, direcciones, cuentas y auditoria.

## Estructura frontend

```text
src/modules/contactos/
  pages/
    ContactosPage.jsx
    ContactoDetailPage.jsx
    ClientesListPage.jsx
    ClientesCreatePage.jsx
    ClientesEditPage.jsx
    ProveedoresListPage.jsx
    ProveedoresCreatePage.jsx
    ProveedoresEditPage.jsx
  components/
    ContactoResumenSection.jsx
    ContactoDireccionesSection.jsx
    ContactoCuentasSection.jsx
    ContactoCommercialSection.jsx
    ContactoAuditSection.jsx
  store/
    api.js
    contactosSlice.js
    hooks.js
    mutations.js
```

## Capas principales

- `store/api.js`
  Endpoints y contratos del modulo.
- `contactosSlice.js`
  Estado compartido para recursos base del modulo.
- `hooks.js`
  Cargas de lectura y detalle.
- `mutations.js`
  Mutaciones UI con toasts y refresh.

## Decisiones UI relevantes

- El detalle del tercero concentra auditoria y subrecursos en una sola vista.
- Los flujos de cliente y proveedor reutilizan secciones comunes del contacto base.
- El modulo mantiene separacion entre listado operativo y detalle consolidado del tercero.

## Estado actual del modulo

El frontend de `contactos` ya esta alineado con el estandar del ERP en:

- separacion clara entre clientes, proveedores y contacto base
- detalle consolidado del tercero
- integracion con auditoria
- estructura de store modular y reutilizable

## Deuda residual baja

- mantener sincronizados contratos frontend/backend cuando cambien reglas de RUT, importacion o inactivos

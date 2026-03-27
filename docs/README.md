# Documentacion Tecnica ERP

## Indice
- [Estandar de Modulo ERP](modulo_estandar_erp.md) - Patron objetivo del ERP, con `productos` como modulo de referencia.
- [Arquitectura Modular ERP](arquitectura_modular_erp.md) - Componentes transversales, principios y estandar de modulos.
- [Autenticacion y Permisos](autenticacion_permisos.md) - JWT + Cookies, autorizacion y multi-tenancy.
- [Auditoria y Trazabilidad](auditoria_trazabilidad.md) - Domain Events y Audit Events con hash chain.
- [Guia Practica de Desarrollo](guia_desarrollo.md) - Testing, consultas, debugging y comandos de gestion.
- [Guia Full-Stack de Modulos](fullstack_module_development.md) - Crear nuevo modulo backend + frontend con ejemplo completo.
- [Plantilla Tecnica de Modulo](modulo_template.md) - Lista de verificacion para documentar un modulo.
- [Arquitectura de Excepciones](exception_architecture.md) - Capas limpias, subclases AppError y manejo global de errores.
- [Importacion Masiva](bulk_import.md) - Endpoints de carga CSV/XLSX.
- [CI/CD con GitHub Actions](ci_cd.md) - Pipeline de integracion continua, artifacts y deploy opcional por webhook.

## Documentacion por modulo

- `backend/apps/productos/README.md` - Contrato backend del maestro de productos.
- `frontend/src/modules/productos/README.md` - Estructura y decisiones UI del maestro de productos.
- `backend/apps/inventario/README.md` - Contrato backend de stock, trazabilidad y documentos operativos.
- `frontend/src/modules/inventario/README.md` - Flujos UI de inventario, reportes y correcciones avanzadas.
- `backend/apps/contactos/README.md` - Contrato backend del maestro de terceros, clientes y proveedores.
- `frontend/src/modules/contactos/README.md` - Estructura frontend del maestro de contactos y terceros.

## Uso recomendado

### Para nuevo desarrollador
1. Leer [Arquitectura Modular ERP](arquitectura_modular_erp.md) en las secciones de componentes transversales y estandar de modulos.
2. Leer [Autenticacion y Permisos](autenticacion_permisos.md) para entender autorizacion y multi-tenant.
3. Leer [Estandar de Modulo ERP](modulo_estandar_erp.md) para entender el patron objetivo vigente.
4. Ver ejemplos existentes, tomando `productos` como referencia principal.

### Para crear modulo nuevo
1. Leer [Guia Full-Stack de Modulos](fullstack_module_development.md).
2. Revisar [Arquitectura Modular ERP](arquitectura_modular_erp.md#estandar-para-nuevos-modulos).
3. Revisar [Estandar de Modulo ERP](modulo_estandar_erp.md) y comparar contra `productos`.
4. Usar [Plantilla Tecnica de Modulo](modulo_template.md) para documentar.
5. Asegurar que las excepciones se levanten correctamente segun [Arquitectura de Excepciones](exception_architecture.md).
6. Validar contra el checklist de `AGENTS.md`.

### Para integrador externo
1. Entender [Autenticacion y Permisos](autenticacion_permisos.md).
2. Consumir eventos via [OutboxService](arquitectura_modular_erp.md#3-outboxservice).
3. Leer [Importacion Masiva](bulk_import.md) si se requiere carga de datos.

### Para auditor o compliance
1. Ver [Auditoria y Trazabilidad](auditoria_trazabilidad.md).
2. Considerar `AuditEvent` como registro append-only con hash chain.
3. Considerar `DomainEvent` como registro funcional del negocio.

## Convenciones de codigo

### Servicios y documentacion
- Todo metodo nuevo en `apps/**/services/*.py` debe incluir docstring breve en espanol tecnico.
- Si hay logica no obvia como idempotencia, concurrencia, `select_for_update()` o tolerancias, agregar comentario corto antes del bloque.
- Evitar comentarios redundantes.

### Excepciones
- Servicios de negocio lanzan solo subclases de `AppError`.
- No importar `rest_framework.exceptions` en `apps/**/services/*.py`.
- No usar `raise ValueError(...)` para reglas de negocio.
- Ver [Arquitectura de Excepciones](exception_architecture.md).

### Importacion masiva
- Toda carga masiva nueva debe seguir el estandar documentado en [Importacion Masiva](bulk_import.md).
- La regla base es usar el mismo endpoint para preview y ejecucion real mediante `dry_run`.
- Reutilizar utilidades de `apps.core.services.bulk_import`.

### Permisos
- Cada ViewSet define `permission_modulo` y `permission_action_map`.
- Las acciones personalizadas se agregan a `permission_action_map`.
- Ver [Autenticacion y Permisos](autenticacion_permisos.md#flujo-de-autorizacion-en-viewset).

## Publicacion en GitHub Pages

Sugerencia:
- Exponer `docs/` dentro del sitio de documentacion.
- Usar esta pagina como indice tecnico de arquitectura.
- Crear paginas por modulo usando [Plantilla Tecnica de Modulo](modulo_template.md).

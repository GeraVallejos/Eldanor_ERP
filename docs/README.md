# Documentacion Tecnica ERP

## Indice
- [Arquitectura Modular ERP](arquitectura_modular_erp.md) — Componentes transversales, principios, estandar de modulos.
- [Autenticacion y Permisos](autenticacion_permisos.md) — JWT + Cookies, autorizacion, multi-tenancy.
- [Auditoria y Trazabilidad](auditoria_trazabilidad.md) — Domain Events, Audit Events con hash chain.
- [Guia Practica de Desarrollo](guia_desarrollo.md) — Testing, consultas, debugging y comandos de gestion.
- [Guia Full-Stack de Modulos](fullstack_module_development.md) — Crear nuevo modulo (backend + frontend) con ejemplo completo.
- [Plantilla Tecnica de Modulo](modulo_template.md) — Lista de verificacion para documentar un modulo.
- [Arquitectura de Excepciones](exception_architecture.md) — Capas limpias, subclases AppError y manejo global de errores.
- [Importacion Masiva](bulk_import.md) — Endpoints de carga CSV/XLSX.
- [CI/CD con GitHub Actions](ci_cd.md) — Pipeline de integracion continua, artifacts y deploy opcional por webhook.

## Uso recomendado

### Para nuevo desarrollador
1. Leer [Arquitectura Modular ERP](arquitectura_modular_erp.md) (seccion "Componentes transversales" + "Estandar para nuevos modulos").
2. Leer [Autenticacion y Permisos](autenticacion_permisos.md) para entender autorizacion.
3. Ver ejemplo de modulo existente (ej. presupuestos, compras).

### Para crear modulo nuevo
1. Lee [Guia Full-Stack de Modulos](fullstack_module_development.md) — Ejemplo completo paso-a-paso.
2. Revisar [Estandar para nuevos modulos](arquitectura_modular_erp.md#estandar-para-nuevos-modulos) en arquitectura.
3. Usar [Plantilla Tecnica de Modulo](modulo_template.md) para documentar.
4. Asegurar excepciones se levantan correctamente (ver [Arquitectura de Excepciones](exception_architecture.md)).
5. Validar contra checklist de AGENTS.md (backend + frontend).

### Para integrador externo (API consumidor)
1. Entender [Autenticacion y Permisos](autenticacion_permisos.md) — como autenticarse y permisos.
2. Consumir eventos via [OutboxService](arquitectura_modular_erp.md#3-outboxservice).
3. Leer [Importacion Masiva](bulk_import.md) si carga datos.

### Para auditor / compliance
1. Ver [Auditoria y Trazabilidad](auditoria_trazabilidad.md) para entender Domain Events + Audit Events.
2. `AuditEvent` append-only con hash chain garantiza integridad.
3. DomainEvent registra eventos funcionales completos.

## Convenciones de codigo

### Servicios y documentacion
- **Docstring obligatorio**: Todo metodo nuevo en `apps/**/services/*.py` debe incluir docstring breve en espanol tecnico.
  - Ej: "Crea presupuesto en estado BORRADOR. Valida cliente activo + items no vacio. Emite DomainEvent."
- **Comentarios para logica no obvia**: Si flujo tiene idempotencia, concurrencia (select_for_update), locks, tolerancias, agregar comentario corto en espanol ANTES del bloque.
- **Evitar redundancia**: NO documentar codigo obvio.

### Excepciones
- Servicios (negocio) lanzan solo `AppError` subclases.
- NO importar `rest_framework.exceptions` en `apps/**/services/*.py`.
- NO usar `raise ValueError(...)` para reglas de negocio; usar `BusinessRuleError`, etc.
- Ver [Arquitectura de Excepciones](exception_architecture.md) para tipos y mapeo HTTP.

### Permisos
- Cada ViewSet define `permission_modulo` y `permission_action_map`.
- Acciones personalizadas agregar a `permission_action_map`.
- Ver [Autenticacion y Permisos - Flujo de autorizacion](autenticacion_permisos.md#flujo-de-autorizacion-en-viewset).

## Publicacion en GitHub Pages
Sugerencia:
- Exponer `docs/` dentro del sitio de documentacion.
- Usar esta pagina como indice tecnico de arquitectura.
- Crear paginas por modulo (`ventas.md`, `tesoreria.md`, `contabilidad.md`) usando [Plantilla Tecnica de Modulo](modulo_template.md).

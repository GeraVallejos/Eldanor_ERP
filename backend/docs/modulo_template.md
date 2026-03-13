# Plantilla Tecnica de Modulo

## Contexto
- Nombre del modulo:
- Objetivo de negocio:
- Alcance funcional (in/out):

## Modelo de dominio
- Entidades principales:
- Reglas invariantes:
- Estados y transiciones:

## Servicios
- Servicio:
  - Metodos:
  - Regla principal por metodo:
  - Excepciones de dominio usadas:

## Integraciones
- Eventos de dominio emitidos (`DomainEvent`):
- Eventos outbox emitidos (`OutboxEvent`):
- Consumidores esperados:

## Seguridad
- Permisos modulo/accion:
- Restricciones multiempresa:
- Reglas de auditoria:

## API
- Endpoints:
- Contratos request/response:
- Errores esperados:

## Pruebas
- Unitarias de servicios:
- API contract tests:
- Casos de concurrencia/idempotencia:

## Operacion
- Observabilidad (logs/eventos):
- Reintentos y recuperacion:
- Backfill / migraciones de datos:

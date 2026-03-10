# Estrategia de Tests Frontend

## Objetivo
Set de pruebas escalable por modulo para cubrir:
- Unit tests de utilidades y slices.
- Integracion entre modulos frontend (ej: `auth` -> `productos`).
- Integracion frontend-backend mediante contratos HTTP mockeados con MSW.

## Estructura
- `src/test/setupTests.js`: ciclo de vida global de Vitest + MSW.
- `src/test/msw/handlers.js`: handlers base de endpoints backend.
- `src/test/msw/server.js`: servidor MSW para entorno Node.
- `src/test/utils/createTestStore.js`: store de prueba con reducers reales.
- `src/test/utils/renderWithProviders.jsx`: helper para testear UI con Redux + Router.

## Convencion por modulo
- Ubicar pruebas en `src/modules/<modulo>/tests/`.
- Nombrar archivos `*.test.js`.
- Para componentes/paginas React usar tambien `*.test.jsx`.
- Separar por capa:
  - `slice`/`thunks`: tests unitarios + contratos HTTP.
  - `pages/components`: tests de integracion de UI cuando aplique.

## Cobertura inicial
- `auth`: slice/thunks.
- `productos`: slice/thunks + integracion entre modulos.
- `contactos`: flujo UI de alta de cliente + contrato de payloads.
- `presupuestos`: validaciones inline UI + creacion con buscadores cliente/producto.

## Patrones recomendados
- Usar `server.use(...)` dentro de cada test para sobrescribir handlers.
- Validar estado final del store y payloads enviados a backend.
- Para integracion entre modulos, despachar acciones de un modulo y validar efectos en otro.

## Scripts
- `npm run test`: modo interactivo.
- `npm run test:run`: ejecucion unica (CI).
- `npm run test:module -- --module <modulo>`: ejecuta solo los tests de un modulo.
- `npm run test:scaffold -- --module <modulo>`: crea la plantilla base CRUD+UX para un modulo nuevo.

## Flujo para nuevo modulo
1. Crear modulo en `src/modules/<modulo>/...`.
2. Ejecutar `npm run test:scaffold -- --module <modulo>`.
3. Completar los TODO en `src/modules/<modulo>/tests/`.
4. Ejecutar `npm run test:module -- --module <modulo>`.
5. Validar suite completa con `npm run test:run`.

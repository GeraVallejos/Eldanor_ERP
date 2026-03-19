# CI/CD en GitHub Actions

Esta guia describe la automatizacion configurada para este ERP y como usarla.

## Que se implemento

- CI: [ci.yml](../.github/workflows/ci.yml)
  - Backend: instala dependencias de CI, valida `permission_action_map` y ejecuta `pytest`.
  - Frontend: ejecuta `npm ci`, `npm run lint` y `npm run test:run`.
- CD: [cd.yml](../.github/workflows/cd.yml)
  - Build en `main` (o manual) y publicacion de artifacts (`frontend-dist`, `backend-source`).
  - Deploy opcional por webhook si existe el secreto `DEPLOY_WEBHOOK_URL`.

## Flujo recomendado

1. Crear rama feature y subir cambios.
2. Abrir Pull Request.
3. Esperar pipeline CI en verde.
4. Hacer merge a `main`.
5. CD genera artifacts y, si hay webhook configurado, dispara despliegue.

## Configuracion minima de secretos

Si quieres despliegue automatico via webhook, agrega en GitHub:

- `DEPLOY_WEBHOOK_URL`: URL del proveedor de deploy (Render, Railway, etc.).

Si no defines ese secreto, el deploy se omite y solo se generan artifacts.

## Settings usados en CI

El backend usa [backend/Eldanor_ERP/settings_ci.py](../backend/Eldanor_ERP/settings_ci.py), que:

- Define variables seguras por defecto para CI.
- Usa SQLite para evitar dependencia de MySQL externo.
- Desactiva hardening no necesario en pruebas (cookies secure/HSTS).
- Evita dependencias de storage cloud en tests.

## Comandos utiles locales

Desde [backend](../backend):

```bash
python scripts/check_permission_action_map.py
pytest -q
```

Desde [frontend](../frontend):

```bash
npm run lint
npm run test:run
```

## Buenas practicas

- No subir secretos en codigo ni en `.env` versionado.
- Mantener `permission_action_map` completo para todas las acciones custom.
- Fallar rapido en CI ante acciones custom sin mapping.
- Agregar tests de autorizacion negativa y tenant isolation para nuevas acciones custom.

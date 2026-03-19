# CI/CD en GitHub Actions

Esta guia describe la automatizacion configurada para este ERP y como usarla.

## Que se implemento

- CI: [ci.yml](../.github/workflows/ci.yml)
  - Backend: instala dependencias de CI, valida `permission_action_map` y ejecuta `pytest`.
  - Frontend: ejecuta `npm ci`, `npm run lint` y `npm run test:run`.
- CD: [cd.yml](../.github/workflows/cd.yml)
  - Build en `main` (o manual) y publicacion de artifacts (`frontend-dist`, `backend-source`).
  - Deploy opcional por webhook si existe el secreto `DEPLOY_WEBHOOK_URL`.
- Auto-merge: [automerge.yml](../.github/workflows/automerge.yml)
  - Habilita auto-merge para PR `dev -> main`.
  - GitHub hace el merge solo cuando todos los checks requeridos estan en verde.
- Branch protection automatizada: [branch-protection.yml](../.github/workflows/branch-protection.yml)
  - Workflow manual que configura reglas de proteccion en `main`.
  - Exige checks Backend/Frontend en verde y aprobacion de PR.

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

## Requisitos para auto-merge

Para que funcione correctamente:

1. En GitHub repo settings, activar **Allow auto-merge**.
2. En branch protection de `main`, marcar checks requeridos (CI backend y frontend).
3. Abrir PR desde `dev` hacia `main`.

Con eso, el workflow habilita auto-merge y GitHub fusiona automaticamente cuando CI queda en verde.

## Automatizar branch protection

1. Ejecutar workflow manual **Configure Branch Protection** desde Actions.
2. Verificar que `main` quede con:
  - checks requeridos: `Backend Tests`, `Frontend Lint and Tests`
  - al menos 1 aprobacion
  - rechazo de force push y delete

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

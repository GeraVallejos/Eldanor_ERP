#!/usr/bin/env node
import { spawnSync } from 'node:child_process'

function getModuleArg(argv) {
  const args = [...argv]

  const moduleFlagIndex = args.findIndex((arg) => arg === '--module' || arg === '-m')
  if (moduleFlagIndex >= 0 && args[moduleFlagIndex + 1]) {
    return args[moduleFlagIndex + 1]
  }

  return args[0]
}

const moduleName = getModuleArg(process.argv.slice(2))

if (!moduleName) {
  console.error('Uso: npm run test:module -- --module <nombre_modulo>')
  process.exit(1)
}

if (!/^[a-zA-Z0-9_-]+$/.test(moduleName)) {
  console.error('Nombre de modulo invalido. Usa solo letras, numeros, guion y guion_bajo.')
  process.exit(1)
}

const pattern = `src/modules/${moduleName}/tests`

const result = spawnSync('npx', ['vitest', 'run', pattern], {
  stdio: 'inherit',
  shell: true,
})

if (typeof result.status === 'number') {
  process.exit(result.status)
}

process.exit(1)

#!/usr/bin/env node
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'

function getModuleArg(argv) {
  const args = [...argv]

  const moduleFlagIndex = args.findIndex((arg) => arg === '--module' || arg === '-m')
  if (moduleFlagIndex >= 0 && args[moduleFlagIndex + 1]) {
    return args[moduleFlagIndex + 1]
  }

  return args[0]
}

function writeIfMissing(filePath, content) {
  try {
    writeFileSync(filePath, content, { encoding: 'utf8', flag: 'wx' })
    return true
  } catch {
    return false
  }
}

const moduleName = getModuleArg(process.argv.slice(2))

if (!moduleName) {
  console.error('Uso: npm run test:scaffold -- --module <nombre_modulo>')
  process.exit(1)
}

if (!/^[a-zA-Z0-9_-]+$/.test(moduleName)) {
  console.error('Nombre de modulo invalido. Usa solo letras, numeros, guion y guion_bajo.')
  process.exit(1)
}

const testDir = join('src', 'modules', moduleName, 'tests')
mkdirSync(testDir, { recursive: true })

const createFilePath = join(testDir, `${moduleName}CreatePage.test.jsx`)
const listFilePath = join(testDir, `${moduleName}ListPage.test.jsx`)
const contractFilePath = join(testDir, `${moduleName}Contract.test.js`)

const createTemplate = `import { describe, it } from 'vitest'\n\ndescribe.skip('${moduleName}/CreatePage', () => {\n  it('crea registro y muestra feedback al usuario', async () => {\n    // TODO: render page, completar formulario, enviar, validar toast+payload\n  })\n\n  it('muestra errores inline de validacion', async () => {\n    // TODO: enviar con campos invalidos y verificar mensajes\n  })\n})\n`

const listTemplate = `import { describe, it } from 'vitest'\n\ndescribe.skip('${moduleName}/ListPage', () => {\n  it('lista registros y permite filtrar/buscar', async () => {\n    // TODO: mock GET list y validar render + filtro\n  })\n\n  it('edita y elimina registros con feedback', async () => {\n    // TODO: validar flujo update/delete y contratos de payload\n  })\n})\n`

const contractTemplate = `import { describe, it } from 'vitest'\n\ndescribe.skip('${moduleName}/API Contract', () => {\n  it('cumple contrato minimo de create/list/update/delete', async () => {\n    // TODO: validar shape de request/response con MSW en endpoints del modulo\n  })\n})\n`

const created = [
  [createFilePath, createTemplate],
  [listFilePath, listTemplate],
  [contractFilePath, contractTemplate],
].map(([filePath, content]) => ({ filePath, created: writeIfMissing(filePath, content) }))

console.log(`Scaffold de tests para modulo "${moduleName}" en ${testDir}`)
for (const file of created) {
  const label = file.created ? 'creado' : 'ya existia'
  console.log(`- ${label}: ${file.filePath}`)
}

const readmePath = join(testDir, 'README.md')
const readmeCreated = writeIfMissing(
  readmePath,
  `# Tests del modulo ${moduleName}\n\n## Checklist minima\n- CRUD basico (create/list/update/delete).\n- Validaciones inline y feedback UX (toasts/mensajes).\n- Contrato frontend-backend (payloads y shape de respuesta).\n`,
)

if (readmeCreated) {
  console.log(`- creado: ${readmePath}`)
}

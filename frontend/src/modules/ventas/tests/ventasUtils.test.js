import { describe, expect, it } from 'vitest'
import { buildErrorMessage, hasPermission, normalizeListResponse } from '@/modules/ventas/utils'

describe('ventas/utils', () => {
  it('normaliza respuestas de lista', () => {
    expect(normalizeListResponse([{ id: 1 }])).toEqual([{ id: 1 }])
    expect(normalizeListResponse({ results: [{ id: 2 }] })).toEqual([{ id: 2 }])
    expect(normalizeListResponse(null)).toEqual([])
  })

  it('valida permisos por codigo y wildcard', () => {
    const userA = { permissions: ['VENTAS.VER'] }
    const userB = { permissions: ['VENTAS.*'] }
    const userC = { permissions: ['*'] }

    expect(hasPermission(userA, 'VENTAS.VER')).toBe(true)
    expect(hasPermission(userA, 'VENTAS.EDITAR')).toBe(false)
    expect(hasPermission(userB, 'VENTAS.EDITAR')).toBe(true)
    expect(hasPermission(userC, 'COMPRAS.VER')).toBe(true)
  })

  it('arma mensajes de error del contrato backend', () => {
    const asString = {
      response: {
        data: {
          detail: 'No se puede emitir sin items.',
          error_code: 'BUSINESS_RULE_ERROR',
        },
      },
    }
    expect(buildErrorMessage(asString)).toBe('No se puede emitir sin items. (BUSINESS_RULE_ERROR)')

    const asObject = {
      response: {
        data: {
          detail: {
            cliente: ['Este campo es obligatorio.'],
          },
          error_code: 'VALIDATION_ERROR',
        },
      },
    }
    expect(buildErrorMessage(asObject)).toBe('Este campo es obligatorio.')
  })
})

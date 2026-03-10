import { beforeEach, describe, expect, it, vi } from 'vitest'
import { toast } from 'sonner'
import { normalizeApiError, notifyGlobalApiError } from '@/api/errors'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
  },
}))

describe('api/errors', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('normaliza mensajes desde detail', () => {
    const error = {
      response: {
        status: 400,
        data: {
          detail: 'Mensaje backend',
        },
      },
    }

    expect(normalizeApiError(error)).toBe('Mensaje backend')
  })

  it('normaliza errores de campo en payload diccionario', () => {
    const error = {
      response: {
        status: 400,
        data: {
          email: ['Email invalido'],
        },
      },
    }

    expect(normalizeApiError(error)).toBe('Email invalido')
  })

  it('retorna fallback de red cuando no hay response', () => {
    expect(normalizeApiError({})).toBe('No pudimos conectar con el servidor. Intenta nuevamente.')
  })

  it('muestra toast global para errores 5xx', () => {
    notifyGlobalApiError({
      response: {
        status: 500,
        data: {
          detail: 'Error interno',
        },
      },
    })

    expect(toast.error).toHaveBeenCalledWith('Error interno')
  })

  it('no muestra toast global para errores 4xx controlados', () => {
    notifyGlobalApiError({
      response: {
        status: 400,
        data: {
          detail: 'Error validacion',
        },
      },
    })

    expect(toast.error).not.toHaveBeenCalled()
  })
})

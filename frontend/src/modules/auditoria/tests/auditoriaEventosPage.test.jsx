import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AuditoriaEventosPage from '@/modules/auditoria/pages/AuditoriaEventosPage'
import { server } from '@/test/msw/server'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

describe('auditoria/AuditoriaEventosPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('carga eventos y permite verificar integridad', async () => {
    server.use(
      http.get('*/auditoria/eventos/', async () =>
        HttpResponse.json({
          count: 1,
          next: null,
          previous: null,
          results: [
            {
              id: 'evt-1',
              module_code: 'COMPRAS',
              action_code: 'APROBAR',
              event_type: 'COMPRA_FACTURA_CONFIRMADA',
              entity_type: 'DOCUMENTO_COMPRA',
              entity_id: 'DOC-1',
              summary: 'Factura confirmada',
              severity: 'INFO',
              creado_por_email: 'admin@eldanor.cl',
              occurred_at: '2026-03-13T12:00:00Z',
              payload: { tipo_documento: 'FACTURA_COMPRA', folio: '123' },
              meta: {},
            },
          ],
        }),
      ),
      http.get('*/auditoria/eventos/integridad/', async () =>
        HttpResponse.json({
          is_valid: true,
          total_events: 18,
          inconsistencies: [],
        }),
      ),
    )

    renderWithProviders(<AuditoriaEventosPage />)

    expect(await screen.findByRole('heading', { name: 'Auditoria central' })).toBeInTheDocument()
    const summaryMatches = await screen.findAllByText('Factura confirmada')
    expect(summaryMatches.length).toBeGreaterThanOrEqual(1)

    await userEvent.click(screen.getByRole('button', { name: 'Herramientas' }))
    await userEvent.click(screen.getByRole('button', { name: /Verificar integridad/i }))

    expect(await screen.findByText('Estado: Valida')).toBeInTheDocument()
    expect(screen.getByText('Total eventos revisados: 18')).toBeInTheDocument()
  })
})
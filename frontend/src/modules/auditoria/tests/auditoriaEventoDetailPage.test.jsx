import { render, screen } from '@testing-library/react'
import { Provider } from 'react-redux'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AuditoriaEventoDetailPage from '@/modules/auditoria/pages/AuditoriaEventoDetailPage'
import { server } from '@/test/msw/server'
import { createTestStore } from '@/test/utils/createTestStore'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

describe('auditoria/AuditoriaEventoDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('carga detalle de evento y renderiza cambios interpretados', async () => {
    server.use(
      http.get('*/auditoria/eventos/evt-1/', async () =>
        HttpResponse.json({
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
          changes: {
            estado: ['BORRADOR', 'CONFIRMADO'],
          },
          payload: { tipo_documento: 'FACTURA_COMPRA', folio: '123' },
          meta: {},
        }),
      ),
    )

    const store = createTestStore()

    render(
      <Provider store={store}>
        <MemoryRouter initialEntries={['/auditoria/eventos/evt-1']}>
          <Routes>
            <Route path="/auditoria/eventos/:id" element={<AuditoriaEventoDetailPage />} />
          </Routes>
        </MemoryRouter>
      </Provider>,
    )

    expect(await screen.findByRole('heading', { name: 'Detalle de evento' })).toBeInTheDocument()
    const summaryMatches = await screen.findAllByText('Factura confirmada')
    expect(summaryMatches.length).toBeGreaterThanOrEqual(1)
    expect(await screen.findByText('estado')).toBeInTheDocument()
    expect(await screen.findByText('CONFIRMADO')).toBeInTheDocument()
  })
})

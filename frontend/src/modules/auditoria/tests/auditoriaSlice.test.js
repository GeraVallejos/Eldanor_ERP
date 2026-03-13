import { describe, expect, it } from 'vitest'
import {
  clearAuditoriaFilters,
  resetAuditoriaState,
  selectAuditoriaDetalleEvento,
  selectAuditoriaEventos,
  selectAuditoriaFilters,
  setAuditoriaDetalleEvento,
  setAuditoriaDetalleStatus,
  setAuditoriaEventos,
  setAuditoriaFilters,
  setAuditoriaIntegrity,
  setAuditoriaPagination,
  setAuditoriaStatus,
} from '@/modules/auditoria/store/auditoriaSlice'
import { createTestStore } from '@/test/utils/createTestStore'

describe('auditoriaSlice', () => {
  it('guarda eventos y paginacion de auditoria', () => {
    const store = createTestStore()

    store.dispatch(
      setAuditoriaEventos([
        { id: 'evt-1', module_code: 'COMPRAS', summary: 'Documento confirmado' },
      ]),
    )
    store.dispatch(
      setAuditoriaPagination({
        count: 10,
        next: '/api/auditoria/eventos/?page=2',
        previous: null,
      }),
    )

    expect(selectAuditoriaEventos(store.getState())).toHaveLength(1)
    expect(store.getState().auditoria.pagination.count).toBe(10)
  })

  it('actualiza y limpia filtros conservando page_size', () => {
    const store = createTestStore()

    store.dispatch(
      setAuditoriaFilters({
        module_code: 'COMPRAS',
        event_type: 'COMPRA_FACTURA_CONFIRMADA',
        page_size: 20,
      }),
    )

    expect(selectAuditoriaFilters(store.getState())).toMatchObject({
      module_code: 'COMPRAS',
      event_type: 'COMPRA_FACTURA_CONFIRMADA',
      page_size: 20,
    })

    store.dispatch(clearAuditoriaFilters())

    expect(selectAuditoriaFilters(store.getState())).toMatchObject({
      module_code: '',
      event_type: '',
      page_size: 20,
      page: 1,
    })
  })

  it('permite setear integridad y resetear estado', () => {
    const store = createTestStore()

    store.dispatch(setAuditoriaStatus('succeeded'))
    store.dispatch(setAuditoriaDetalleStatus('succeeded'))
    store.dispatch(setAuditoriaDetalleEvento({ id: 'evt-42', summary: 'Detalle cargado' }))
    store.dispatch(setAuditoriaIntegrity({ is_valid: true, total_events: 3, inconsistencies: [] }))

    expect(store.getState().auditoria.status).toBe('succeeded')
    expect(store.getState().auditoria.detalleStatus).toBe('succeeded')
    expect(selectAuditoriaDetalleEvento(store.getState())?.id).toBe('evt-42')
    expect(store.getState().auditoria.integrity?.is_valid).toBe(true)

    store.dispatch(resetAuditoriaState())

    expect(store.getState().auditoria.status).toBe('idle')
    expect(store.getState().auditoria.detalleStatus).toBe('idle')
    expect(store.getState().auditoria.detalleEvento).toBeNull()
    expect(store.getState().auditoria.integrity).toBeNull()
    expect(store.getState().auditoria.eventos).toEqual([])
  })
})
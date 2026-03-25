import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import InventarioBodegasPage from '@/modules/inventario/pages/InventarioBodegasPage'
import { server } from '@/test/msw/server'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

const preloadedState = {
  auth: {
    user: {
      id: 'user-1',
      permissions: ['INVENTARIO.CREAR', 'INVENTARIO.EDITAR', 'INVENTARIO.BORRAR'],
    },
    empresas: [],
    empresasStatus: 'idle',
    empresasError: null,
    changingEmpresaId: null,
    isAuthenticated: true,
    status: 'succeeded',
    bootstrapStatus: 'succeeded',
    error: null,
  },
}

describe('inventario/InventarioBodegasPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('crea y edita bodegas con nombres normalizados', async () => {
    const bodegas = [{ id: 'bod-1', nombre: 'PRINCIPAL', activa: true }]
    let lastCreatedPayload = null
    let lastUpdatedPayload = null

    server.use(
      http.get('*/bodegas/', async () => HttpResponse.json(bodegas)),
      http.post('*/bodegas/', async ({ request }) => {
        lastCreatedPayload = await request.json()
        bodegas.push({ id: 'bod-2', ...lastCreatedPayload })
        return HttpResponse.json({ id: 'bod-2', ...lastCreatedPayload }, { status: 201 })
      }),
      http.patch('*/bodegas/:id/', async ({ params, request }) => {
        lastUpdatedPayload = await request.json()
        const index = bodegas.findIndex((item) => item.id === params.id)
        bodegas[index] = { ...bodegas[index], ...lastUpdatedPayload }
        return HttpResponse.json(bodegas[index])
      }),
    )

    renderWithProviders(<InventarioBodegasPage />, { preloadedState })

    expect(await screen.findByText('PRINCIPAL')).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText('Nombre'), 'casa matriz')
    await userEvent.click(screen.getByRole('button', { name: 'Crear bodega' }))

    await waitFor(() => {
      expect(lastCreatedPayload).toEqual({ nombre: 'CASA MATRIZ', activa: true })
    })

    expect(await screen.findByText('CASA MATRIZ')).toBeInTheDocument()

    await userEvent.click(screen.getAllByRole('button', { name: 'Editar' })[0])
    const nombreInput = screen.getByLabelText('Nombre')
    await userEvent.clear(nombreInput)
    await userEvent.type(nombreInput, 'sucursal sur')
    await userEvent.click(screen.getByRole('button', { name: 'Actualizar bodega' }))

    await waitFor(() => {
      expect(lastUpdatedPayload).toEqual({ nombre: 'SUCURSAL SUR', activa: true })
    })
  })

  it('muestra inactivacion o eliminacion segun respuesta del backend', async () => {
    const bodegas = [
      { id: 'bod-1', nombre: 'PRINCIPAL', activa: true, tiene_uso_historico: true },
      { id: 'bod-2', nombre: 'SUCURSAL', activa: true, tiene_uso_historico: false },
    ]

    server.use(
      http.get('*/bodegas/', async () => HttpResponse.json(bodegas)),
      http.delete('*/bodegas/bod-1/', async () => {
        const index = bodegas.findIndex((item) => item.id === 'bod-1')
        bodegas[index] = { ...bodegas[index], activa: false }
        return HttpResponse.json({ deleted: false, bodega: bodegas[index] }, { status: 200 })
      }),
      http.delete('*/bodegas/bod-2/', async () => {
        const index = bodegas.findIndex((item) => item.id === 'bod-2')
        bodegas.splice(index, 1)
        return new HttpResponse(null, { status: 204 })
      }),
    )

    renderWithProviders(<InventarioBodegasPage />, { preloadedState })

    expect(await screen.findByText('PRINCIPAL')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Inactivar' }))
    expect(await screen.findByText(/se inactivara para preservar la trazabilidad/i)).toBeInTheDocument()
    await userEvent.click(await screen.findByRole('button', { name: 'Confirmar' }))

    await waitFor(() => {
      expect(screen.getByText('Inactiva')).toBeInTheDocument()
    })

    await userEvent.click(await screen.findByRole('button', { name: 'Eliminar' }))
    expect(await screen.findByText(/se eliminara definitivamente/i)).toBeInTheDocument()
    await userEvent.click(await screen.findByRole('button', { name: 'Confirmar' }))

    await waitFor(() => {
      expect(screen.queryByText('SUCURSAL')).not.toBeInTheDocument()
    })
  })

  it('filtra bodegas por estado', async () => {
    const bodegas = [
      { id: 'bod-1', nombre: 'PRINCIPAL', activa: true, tiene_uso_historico: false },
      { id: 'bod-2', nombre: 'ARCHIVO', activa: false, tiene_uso_historico: true },
    ]

    server.use(http.get('*/bodegas/', async () => HttpResponse.json(bodegas)))

    renderWithProviders(<InventarioBodegasPage />, { preloadedState })

    expect(await screen.findByText('PRINCIPAL')).toBeInTheDocument()
    expect(screen.getByText('ARCHIVO')).toBeInTheDocument()

    await userEvent.selectOptions(screen.getByLabelText('Estado'), 'INACTIVAS')

    await waitFor(() => {
      expect(screen.queryByText('PRINCIPAL')).not.toBeInTheDocument()
      expect(screen.getByText('ARCHIVO')).toBeInTheDocument()
    })
  })
})

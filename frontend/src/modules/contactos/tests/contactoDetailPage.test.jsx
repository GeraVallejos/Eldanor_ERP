import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import ContactoDetailPage from '@/modules/contactos/pages/ContactoDetailPage'
import { server } from '@/test/msw/server'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

describe('contactos/ContactoDetailPage', () => {
  it('muestra ficha unificada con datos de cliente, proveedor y relaciones asociadas', async () => {
    server.use(
      http.get('*/contactos/c-1/detalle-tercero/', async () =>
        HttpResponse.json({
          id: 'c-1',
          nombre: 'Comercial Andes SpA',
          razon_social: 'Comercial Andes SpA',
          rut: '12.345.678-5',
          tipo: 'EMPRESA',
          email: 'contacto@andes.cl',
          telefono: '22223333',
          celular: '99998888',
          activo: true,
          notas: 'Cliente y proveedor estrategico',
          cliente: {
            id: 'cli-1',
            contacto: 'c-1',
            limite_credito: 500000,
            dias_credito: 30,
            categoria_cliente: 'ORO',
            segmento: 'RETAIL',
          },
          proveedor: {
            id: 'prov-1',
            contacto: 'c-1',
            giro: 'Servicios industriales',
            vendedor_contacto: 'Ana Perez',
            dias_credito: 15,
          },
          direcciones: [
            {
              id: 'dir-1',
              contacto: 'c-1',
              tipo: 'FACTURACION',
              direccion: 'Av. Principal 123',
              comuna: 'Providencia',
              ciudad: 'Santiago',
              region: 'RM',
              pais: 'Chile',
            },
          ],
          cuentas_bancarias: [
            {
              id: 'cb-1',
              contacto: 'c-1',
              banco: 'Banco Estado',
              tipo_cuenta: 'CORRIENTE',
              numero_cuenta: '123456',
              titular: 'Comercial Andes SpA',
              rut_titular: '12.345.678-5',
            },
          ],
        }),
      ),
    )

    renderWithProviders(
      <Routes>
        <Route path="/contactos/terceros/:id" element={<ContactoDetailPage />} />
      </Routes>,
      {
        initialEntries: ['/contactos/terceros/c-1'],
        preloadedState: {
          auth: {
            user: {
              id: 10,
              email: 'admin@erp.test',
              permissions: ['CONTACTOS.VER', 'CONTACTOS.EDITAR'],
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
        },
      },
    )

    expect(await screen.findByRole('heading', { name: 'Comercial Andes SpA' })).toBeInTheDocument()
    expect(screen.getByText(/Cliente \+ Proveedor/i)).toBeInTheDocument()
    expect(screen.getByText('Cliente y proveedor estrategico')).toBeInTheDocument()
    expect(screen.getByText('Servicios industriales')).toBeInTheDocument()
    expect(screen.getByText('Av. Principal 123')).toBeInTheDocument()
    expect(screen.getByText('Banco Estado')).toBeInTheDocument()
  })

  it('permite agregar una direccion desde la ficha del tercero', async () => {
    const direcciones = []
    let direccionPayload = null

    server.use(
      http.get('*/contactos/c-1/detalle-tercero/', async () =>
        HttpResponse.json({
          id: 'c-1',
          nombre: 'Tercero Editable',
          razon_social: '',
          rut: '12.345.678-5',
          tipo: 'EMPRESA',
          email: 'editable@test.cl',
          telefono: '',
          celular: '',
          activo: true,
          notas: '',
          cliente: null,
          proveedor: null,
          direcciones,
          cuentas_bancarias: [],
        }),
      ),
      http.post('*/direcciones/', async ({ request }) => {
        direccionPayload = await request.json()
        const nuevaDireccion = {
          id: 'dir-2',
          ...direccionPayload,
          region: direccionPayload.region,
          pais: direccionPayload.pais,
        }
        direcciones.push(nuevaDireccion)
        return HttpResponse.json(nuevaDireccion, { status: 201 })
      }),
    )

    renderWithProviders(
      <Routes>
        <Route path="/contactos/terceros/:id" element={<ContactoDetailPage />} />
      </Routes>,
      {
        initialEntries: ['/contactos/terceros/c-1'],
        preloadedState: {
          auth: {
            user: {
              id: 10,
              email: 'admin@erp.test',
              permissions: ['CONTACTOS.VER', 'CONTACTOS.EDITAR'],
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
        },
      },
    )

    expect(await screen.findByRole('heading', { name: 'Tercero Editable' })).toBeInTheDocument()

    await userEvent.selectOptions(screen.getByLabelText('Tipo'), 'DESPACHO')
    await userEvent.type(screen.getByLabelText('Direccion'), 'Calle Nueva 456')
    await userEvent.type(screen.getByLabelText('Comuna'), 'Las Condes')
    await userEvent.type(screen.getByLabelText('Ciudad'), 'Santiago')
    await userEvent.type(screen.getByLabelText('Region'), 'RM')

    await userEvent.click(screen.getByRole('button', { name: 'Agregar direccion' }))

    await waitFor(() => {
      expect(screen.getByText('Calle Nueva 456')).toBeInTheDocument()
    })

    expect(direccionPayload).toMatchObject({
      contacto: 'c-1',
      tipo: 'DESPACHO',
      direccion: 'Calle Nueva 456',
      comuna: 'Las Condes',
      ciudad: 'Santiago',
      region: 'RM',
    })
  })

  it('permite editar una direccion existente desde la ficha del tercero', async () => {
    const direcciones = [
      {
        id: 'dir-1',
        contacto: 'c-1',
        tipo: 'FACTURACION',
        direccion: 'Av. Inicial 100',
        comuna: 'Providencia',
        ciudad: 'Santiago',
        region: 'RM',
        pais: 'Chile',
      },
    ]
    let direccionPayload = null

    server.use(
      http.get('*/contactos/c-1/detalle-tercero/', async () =>
        HttpResponse.json({
          id: 'c-1',
          nombre: 'Tercero Editable',
          razon_social: '',
          rut: '12.345.678-5',
          tipo: 'EMPRESA',
          email: 'editable@test.cl',
          telefono: '',
          celular: '',
          activo: true,
          notas: '',
          cliente: null,
          proveedor: null,
          direcciones,
          cuentas_bancarias: [],
        }),
      ),
      http.patch('*/direcciones/dir-1/', async ({ request }) => {
        direccionPayload = await request.json()
        direcciones[0] = {
          ...direcciones[0],
          ...direccionPayload,
        }
        return HttpResponse.json(direcciones[0])
      }),
    )

    renderWithProviders(
      <Routes>
        <Route path="/contactos/terceros/:id" element={<ContactoDetailPage />} />
      </Routes>,
      {
        initialEntries: ['/contactos/terceros/c-1'],
        preloadedState: {
          auth: {
            user: {
              id: 10,
              email: 'admin@erp.test',
              permissions: ['CONTACTOS.VER', 'CONTACTOS.EDITAR'],
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
        },
      },
    )

    expect(await screen.findByText('Av. Inicial 100')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Editar' }))
    await userEvent.clear(screen.getByLabelText('Direccion editada'))
    await userEvent.type(screen.getByLabelText('Direccion editada'), 'Av. Actualizada 200')
    await userEvent.clear(screen.getByLabelText('Comuna editada'))
    await userEvent.type(screen.getByLabelText('Comuna editada'), 'Las Condes')

    await userEvent.click(screen.getByRole('button', { name: 'Guardar direccion' }))

    await waitFor(() => {
      expect(screen.getByText('Av. Actualizada 200')).toBeInTheDocument()
    })

    expect(direccionPayload).toMatchObject({
      direccion: 'Av. Actualizada 200',
      comuna: 'Las Condes',
      ciudad: 'Santiago',
      tipo: 'FACTURACION',
    })
  })

  it('permite editar una cuenta bancaria existente desde la ficha del tercero', async () => {
    const cuentasBancarias = [
      {
        id: 'cb-1',
        contacto: 'c-1',
        banco: 'Banco Estado',
        tipo_cuenta: 'CORRIENTE',
        numero_cuenta: '123456',
        titular: 'Comercial Andes SpA',
        rut_titular: '12.345.678-5',
        activa: true,
      },
    ]
    let cuentaPayload = null

    server.use(
      http.get('*/contactos/c-1/detalle-tercero/', async () =>
        HttpResponse.json({
          id: 'c-1',
          nombre: 'Tercero Bancario',
          razon_social: '',
          rut: '12.345.678-5',
          tipo: 'EMPRESA',
          email: 'editable@test.cl',
          telefono: '',
          celular: '',
          activo: true,
          notas: '',
          cliente: null,
          proveedor: null,
          direcciones: [],
          cuentas_bancarias: cuentasBancarias,
        }),
      ),
      http.patch('*/contactos/cuentas-bancarias/cb-1/', async ({ request }) => {
        cuentaPayload = await request.json()
        cuentasBancarias[0] = {
          ...cuentasBancarias[0],
          ...cuentaPayload,
        }
        return HttpResponse.json(cuentasBancarias[0])
      }),
    )

    renderWithProviders(
      <Routes>
        <Route path="/contactos/terceros/:id" element={<ContactoDetailPage />} />
      </Routes>,
      {
        initialEntries: ['/contactos/terceros/c-1'],
        preloadedState: {
          auth: {
            user: {
              id: 10,
              email: 'admin@erp.test',
              permissions: ['CONTACTOS.VER', 'CONTACTOS.EDITAR'],
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
        },
      },
    )

    expect(await screen.findByText('Banco Estado')).toBeInTheDocument()

    const editButtons = screen.getAllByRole('button', { name: 'Editar' })
    await userEvent.click(editButtons[0])
    await userEvent.clear(screen.getByLabelText('Banco editado'))
    await userEvent.type(screen.getByLabelText('Banco editado'), 'Banco de Chile')
    await userEvent.clear(screen.getByLabelText('Numero de cuenta editado'))
    await userEvent.type(screen.getByLabelText('Numero de cuenta editado'), '999888')
    await userEvent.click(screen.getByRole('checkbox', { name: 'Cuenta activa' }))

    await userEvent.click(screen.getByRole('button', { name: 'Guardar cuenta' }))

    await waitFor(() => {
      expect(screen.getByText('Banco de Chile')).toBeInTheDocument()
    })

    expect(cuentaPayload).toMatchObject({
      banco: 'Banco de Chile',
      numero_cuenta: '999888',
      activa: false,
      tipo_cuenta: 'CORRIENTE',
    })
  })

  it('solicita confirmacion antes de eliminar una direccion desde la ficha del tercero', async () => {
    const direcciones = [
      {
        id: 'dir-1',
        contacto: 'c-1',
        tipo: 'FACTURACION',
        direccion: 'Av. Inicial 100',
        comuna: 'Providencia',
        ciudad: 'Santiago',
        region: 'RM',
        pais: 'Chile',
      },
    ]

    server.use(
      http.get('*/contactos/c-1/detalle-tercero/', async () =>
        HttpResponse.json({
          id: 'c-1',
          nombre: 'Tercero Editable',
          razon_social: '',
          rut: '12.345.678-5',
          tipo: 'EMPRESA',
          email: 'editable@test.cl',
          telefono: '',
          celular: '',
          activo: true,
          notas: '',
          cliente: null,
          proveedor: null,
          direcciones,
          cuentas_bancarias: [],
        }),
      ),
      http.delete('*/direcciones/dir-1/', async () => {
        direcciones.splice(0, 1)
        return new HttpResponse(null, { status: 204 })
      }),
    )

    renderWithProviders(
      <Routes>
        <Route path="/contactos/terceros/:id" element={<ContactoDetailPage />} />
      </Routes>,
      {
        initialEntries: ['/contactos/terceros/c-1'],
        preloadedState: {
          auth: {
            user: {
              id: 10,
              email: 'admin@erp.test',
              permissions: ['CONTACTOS.VER', 'CONTACTOS.EDITAR', 'CONTACTOS.BORRAR'],
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
        },
      },
    )

    expect(await screen.findByText('Av. Inicial 100')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Eliminar' }))
    expect(await screen.findByText('Se eliminara la direccion del tercero y se registrara su trazabilidad en auditoria.')).toBeInTheDocument()

    await userEvent.click(screen.getAllByRole('button', { name: 'Eliminar' })[1])

    await waitFor(() => {
      expect(screen.queryByText('Av. Inicial 100')).not.toBeInTheDocument()
    })
  })

  it('muestra trazabilidad consolidada cuando el usuario tiene permiso de auditoria', async () => {
    server.use(
      http.get('*/contactos/c-1/detalle-tercero/', async () =>
        HttpResponse.json({
          id: 'c-1',
          nombre: 'Tercero Auditado',
          razon_social: '',
          rut: '12.345.678-5',
          tipo: 'EMPRESA',
          email: 'audit@test.cl',
          telefono: '',
          celular: '',
          activo: true,
          notas: '',
          cliente: {
            id: 'cli-1',
            contacto: 'c-1',
            limite_credito: 500000,
            dias_credito: 30,
            categoria_cliente: 'ORO',
            segmento: 'RETAIL',
          },
          proveedor: {
            id: 'prov-1',
            contacto: 'c-1',
            giro: 'Servicios industriales',
            vendedor_contacto: 'Ana Perez',
            dias_credito: 15,
          },
          direcciones: [
            {
              id: 'dir-1',
              contacto: 'c-1',
              tipo: 'COMERCIAL',
              direccion: 'Av. Operativa 100',
              comuna: 'Providencia',
              ciudad: 'Santiago',
              region: 'RM',
              pais: 'Chile',
            },
          ],
          cuentas_bancarias: [
            {
              id: 'cb-1',
              contacto: 'c-1',
              banco: 'Banco Estado',
              tipo_cuenta: 'CORRIENTE',
              numero_cuenta: '123456',
              titular: 'Tercero Auditado',
              rut_titular: '12.345.678-5',
              activa: true,
            },
          ],
        }),
      ),
      http.get('*/contactos/c-1/auditoria/', async () =>
        HttpResponse.json([
          {
            id: 'evt-direccion',
            event_type: 'DIRECCION_ACTUALIZADA',
            severity: 'ERROR',
            entity_type: 'DIRECCION',
            entity_id: 'dir-1',
            summary: 'Se actualizo la comuna de la direccion comercial.',
            creado_por_email: 'admin@erp.test',
            occurred_at: '2026-03-24T15:00:00Z',
          },
          {
            id: 'evt-cliente',
            event_type: 'CLIENTE_ACTUALIZADO',
            severity: 'WARNING',
            entity_type: 'CLIENTE',
            entity_id: 'cli-1',
            summary: 'Se ajusto el limite de credito.',
            creado_por_email: 'admin@erp.test',
            occurred_at: '2026-03-24T14:00:00Z',
          },
          {
            id: 'evt-contacto',
            event_type: 'CONTACTO_ACTUALIZADO',
            severity: 'INFO',
            entity_type: 'CONTACTO',
            entity_id: 'c-1',
            summary: 'Se actualizo el email del contacto.',
            creado_por_email: 'admin@erp.test',
            occurred_at: '2026-03-24T13:00:00Z',
          },
          {
            id: 'evt-proveedor',
            event_type: 'PROVEEDOR_ACTUALIZADO',
            severity: 'INFO',
            entity_type: 'PROVEEDOR',
            entity_id: 'prov-1',
            summary: 'Se ajustaron los dias de credito.',
            creado_por_email: 'admin@erp.test',
            occurred_at: '2026-03-24T12:00:00Z',
          },
          {
            id: 'evt-cuenta',
            event_type: 'CUENTA_BANCARIA_ACTUALIZADA',
            severity: 'CRITICAL',
            entity_type: 'CUENTA_BANCARIA',
            entity_id: 'cb-1',
            summary: 'Se desactivo temporalmente la cuenta bancaria.',
            creado_por_email: 'admin@erp.test',
            occurred_at: '2026-03-24T11:00:00Z',
          },
        ]),
      ),
    )

    renderWithProviders(
      <Routes>
        <Route path="/contactos/terceros/:id" element={<ContactoDetailPage />} />
      </Routes>,
      {
        initialEntries: ['/contactos/terceros/c-1'],
        preloadedState: {
          auth: {
            user: {
              id: 10,
              email: 'admin@erp.test',
              permissions: ['CONTACTOS.VER', 'AUDITORIA.VER'],
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
        },
      },
    )

    expect(await screen.findByRole('heading', { name: 'Tercero Auditado' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Auditoria' }))
    expect(await screen.findByText('Trazabilidad')).toBeInTheDocument()
    expect(screen.getByText('Se ajusto el limite de credito.')).toBeInTheDocument()
    expect(screen.getByText('Se actualizo la comuna de la direccion comercial.')).toBeInTheDocument()
    expect(screen.getByText('Se desactivo temporalmente la cuenta bancaria.')).toBeInTheDocument()
    expect(screen.getByText('Mostrando 5 de 5 eventos consolidados.')).toBeInTheDocument()
    expect(screen.getByText('WARNING')).toBeInTheDocument()
    expect(screen.getByText('CRITICAL')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Ver evento' })).toHaveLength(5)
    expect(screen.getByRole('link', { name: 'Abrir auditoria central' })).toHaveAttribute('href', '/auditoria/eventos')

    await userEvent.click(screen.getAllByRole('button', { name: 'Finanzas' })[1])
    expect(screen.getByText('Mostrando 1 de 5 eventos consolidados.')).toBeInTheDocument()
    expect(screen.getByText('Se desactivo temporalmente la cuenta bancaria.')).toBeInTheDocument()
    expect(screen.queryByText('Se ajusto el limite de credito.')).not.toBeInTheDocument()
  })

  it('permite navegar entre secciones de la ficha del tercero', async () => {
    server.use(
      http.get('*/contactos/c-1/detalle-tercero/', async () =>
        HttpResponse.json({
          id: 'c-1',
          nombre: 'Tercero Seccionado',
          razon_social: '',
          rut: '12.345.678-5',
          tipo: 'EMPRESA',
          email: 'secciones@test.cl',
          telefono: '',
          celular: '',
          activo: true,
          notas: '',
          cliente: null,
          proveedor: null,
          direcciones: [
            {
              id: 'dir-1',
              contacto: 'c-1',
              tipo: 'COMERCIAL',
              direccion: 'Av. Operativa 100',
              comuna: 'Providencia',
              ciudad: 'Santiago',
              region: 'RM',
              pais: 'Chile',
            },
          ],
          cuentas_bancarias: [
            {
              id: 'cb-1',
              contacto: 'c-1',
              banco: 'Banco Estado',
              tipo_cuenta: 'CORRIENTE',
              numero_cuenta: '123456',
              titular: 'Tercero Seccionado',
              rut_titular: '12.345.678-5',
              activa: true,
            },
          ],
        }),
      ),
    )

    renderWithProviders(
      <Routes>
        <Route path="/contactos/terceros/:id" element={<ContactoDetailPage />} />
      </Routes>,
      {
        initialEntries: ['/contactos/terceros/c-1'],
        preloadedState: {
          auth: {
            user: {
              id: 10,
              email: 'admin@erp.test',
              permissions: ['CONTACTOS.VER', 'CONTACTOS.EDITAR'],
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
        },
      },
    )

    expect(await screen.findByRole('heading', { name: 'Tercero Seccionado' })).toBeInTheDocument()
    expect(screen.getByText('Resumen maestro')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Operacion' }))
    expect(await screen.findByText('Direcciones')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Finanzas' }))
    expect(await screen.findByText('Cuentas bancarias')).toBeInTheDocument()
  })
})

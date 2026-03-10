import { http, HttpResponse } from 'msw'

export const defaultHandlers = [
  http.post('*/token/', async () => {
    return HttpResponse.json({
      user: {
        id: 1,
        email: 'admin@eldanor.cl',
      },
    })
  }),
  http.get('*/auth/me/', async () => {
    return HttpResponse.json({
      user: {
        id: 1,
        email: 'admin@eldanor.cl',
      },
    })
  }),
  http.post('*/auth/logout/', async () => HttpResponse.json({}, { status: 200 })),
  http.get('*/empresas-usuario/', async () => {
    return HttpResponse.json([
      { id: 10, nombre: 'Empresa 1' },
      { id: 11, nombre: 'Empresa 2' },
    ])
  }),
  http.post('*/cambiar-empresa-activa/', async () => HttpResponse.json({}, { status: 200 })),
  http.get('*/productos/', async () => {
    return HttpResponse.json([
      {
        id: 100,
        nombre: 'Servicio de poda',
        sku: 'SERV-001',
        tipo: 'SERVICIO',
        precio_referencia: 15000,
        precio_costo: 7000,
        stock_actual: 0,
        maneja_inventario: false,
        activo: true,
      },
    ])
  }),
  http.post('*/productos/', async ({ request }) => {
    const payload = await request.json()
    return HttpResponse.json(
      {
        id: 101,
        ...payload,
      },
      { status: 201 },
    )
  }),
  http.get('*/categorias/', async () => {
    return HttpResponse.json([{ id: 1, nombre: 'General' }])
  }),
  http.get('*/impuestos/', async () => {
    return HttpResponse.json([{ id: 1, nombre: 'IVA', porcentaje: 19 }])
  }),
]

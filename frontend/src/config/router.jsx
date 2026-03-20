import { Suspense, lazy } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import ERPLayout from '@/layouts/ERPLayout'
import PrivateRoute from '@/modules/auth/components/PrivateRoute'
import PublicOnlyRoute from '@/modules/auth/components/PublicOnlyRoute'

const LoginPage = lazy(() => import('@/modules/auth/pages/LoginPage'))
const ClientesCreatePage = lazy(() => import('@/modules/contactos/pages/ClientesCreatePage'))
const ClientesListPage = lazy(() => import('@/modules/contactos/pages/ClientesListPage'))
const ProveedoresCreatePage = lazy(() => import('@/modules/contactos/pages/ProveedoresCreatePage'))
const ProveedoresListPage = lazy(() => import('@/modules/contactos/pages/ProveedoresListPage'))
const PresupuestosCreatePage = lazy(() => import('@/modules/presupuestos/pages/PresupuestosCreatePage'))
const PresupuestosEditPage = lazy(() => import('@/modules/presupuestos/pages/PresupuestosEditPage'))
const PresupuestosListPage = lazy(() => import('@/modules/presupuestos/pages/PresupuestosListPage'))
const PresupuestoTrazabilidadPage = lazy(() => import('@/modules/presupuestos/pages/PresupuestoTrazabilidadPage'))
const ComprasOrdenesListPage = lazy(() => import('@/modules/compras/pages/ComprasOrdenesListPage'))
const ComprasOrdenesCreatePage = lazy(() => import('@/modules/compras/pages/ComprasOrdenesCreatePage'))
const ComprasOrdenesDetailPage = lazy(() => import('@/modules/compras/pages/ComprasOrdenesDetailPage'))
const ComprasDocumentosListPage = lazy(() => import('@/modules/compras/pages/ComprasDocumentosListPage'))
const ComprasDocumentosCreatePage = lazy(() => import('@/modules/compras/pages/ComprasDocumentosCreatePage'))
const ComprasDocumentosDetailPage = lazy(() => import('@/modules/compras/pages/ComprasDocumentosDetailPage'))
const ComprasRecepcionesListPage = lazy(() => import('@/modules/compras/pages/ComprasRecepcionesListPage'))
const ComprasRecepcionesCreatePage = lazy(() => import('@/modules/compras/pages/ComprasRecepcionesCreatePage'))
const ContabilidadAsientoDetailPage = lazy(() => import('@/modules/contabilidad/pages/ContabilidadAsientoDetailPage'))
const ContabilidadAsientosPage = lazy(() => import('@/modules/contabilidad/pages/ContabilidadAsientosPage'))
const ContabilidadPlanPage = lazy(() => import('@/modules/contabilidad/pages/ContabilidadPlanPage'))
const ContabilidadReportesPage = lazy(() => import('@/modules/contabilidad/pages/ContabilidadReportesPage'))
const AuditoriaEventosPage = lazy(() => import('@/modules/auditoria/pages/AuditoriaEventosPage'))
const AuditoriaEventoDetailPage = lazy(() => import('@/modules/auditoria/pages/AuditoriaEventoDetailPage'))
const AdministracionPermisosPage = lazy(() => import('@/modules/administracion/pages/AdministracionPermisosPage'))
const AdministracionSiiPage = lazy(() => import('@/modules/administracion/pages/AdministracionSiiPage'))
const InventarioBodegasPage = lazy(() => import('@/modules/inventario/pages/InventarioBodegasPage'))
const InventarioKardexPage = lazy(() => import('@/modules/inventario/pages/InventarioKardexPage'))
const InventarioResumenPage = lazy(() => import('@/modules/inventario/pages/InventarioResumenPage'))
const TesoreriaBancosPage = lazy(() => import('@/modules/tesoreria/pages/TesoreriaBancosPage'))
const TesoreriaCuentasPage = lazy(() => import('@/modules/tesoreria/pages/TesoreriaCuentasPage'))
const TesoreriaMonedasPage = lazy(() => import('@/modules/tesoreria/pages/TesoreriaMonedasPage'))
const TesoreriaTipoCambioPage = lazy(() => import('@/modules/tesoreria/pages/TesoreriaTipoCambioPage'))
const VentasPedidosListPage = lazy(() => import('@/modules/ventas/pages/VentasPedidosListPage'))
const VentasPedidosFormPage = lazy(() => import('@/modules/ventas/pages/VentasPedidosFormPage'))
const VentasPedidosDetailPage = lazy(() => import('@/modules/ventas/pages/VentasPedidosDetailPage'))
const VentasGuiasListPage = lazy(() => import('@/modules/ventas/pages/VentasGuiasListPage'))
const VentasGuiasFormPage = lazy(() => import('@/modules/ventas/pages/VentasGuiasFormPage'))
const VentasFacturasListPage = lazy(() => import('@/modules/ventas/pages/VentasFacturasListPage'))
const VentasFacturasFormPage = lazy(() => import('@/modules/ventas/pages/VentasFacturasFormPage'))
const VentasNotasListPage = lazy(() => import('@/modules/ventas/pages/VentasNotasListPage'))
const VentasNotasFormPage = lazy(() => import('@/modules/ventas/pages/VentasNotasFormPage'))
const ProductosCreatePage = lazy(() => import('@/modules/productos/pages/ProductosCreatePage'))
const ProductosCategoriasPage = lazy(() => import('@/modules/productos/pages/ProductosCategoriasPage'))
const ProductosImpuestosPage = lazy(() => import('@/modules/productos/pages/ProductosImpuestosPage'))
const ProductosListasPrecioPage = lazy(() => import('@/modules/productos/pages/ProductosListasPrecioPage'))
const ProductosListPage = lazy(() => import('@/modules/productos/pages/ProductosListPage'))
const NotFoundPage = lazy(() => import('@/modules/shared/pages/NotFoundPage'))

function page(LazyPage) {
  const RoutePage = LazyPage
  return (
    <Suspense fallback={<p className="p-4 text-sm text-muted-foreground">Cargando...</p>}>
      <RoutePage />
    </Suspense>
  )
}

const router = createBrowserRouter([
  {
    element: <PrivateRoute />,
    children: [
      {
        path: '/',
        element: <ERPLayout />,
        children: [
          { index: true, element: page(ProductosListPage) },
          { path: 'contactos', element: page(ClientesListPage) },
          { path: 'contactos/clientes', element: page(ClientesListPage) },
          { path: 'contactos/clientes/nuevo', element: page(ClientesCreatePage) },
          { path: 'contactos/proveedores', element: page(ProveedoresListPage) },
          { path: 'contactos/proveedores/nuevo', element: page(ProveedoresCreatePage) },
          { path: 'presupuestos', element: page(PresupuestosListPage) },
          { path: 'presupuestos/nuevo', element: page(PresupuestosCreatePage) },
          { path: 'presupuestos/:id/editar', element: page(PresupuestosEditPage) },
          { path: 'presupuestos/:id/trazabilidad', element: page(PresupuestoTrazabilidadPage) },
          { path: 'productos', element: page(ProductosListPage) },
          { path: 'productos/nuevo', element: page(ProductosCreatePage) },
          { path: 'productos/categorias', element: page(ProductosCategoriasPage) },
          { path: 'productos/impuestos', element: page(ProductosImpuestosPage) },
          { path: 'productos/listas-precio', element: page(ProductosListasPrecioPage) },
          { path: 'compras/ordenes', element: page(ComprasOrdenesListPage) },
          { path: 'compras/ordenes/nuevo', element: page(ComprasOrdenesCreatePage) },
          { path: 'compras/ordenes/:id', element: page(ComprasOrdenesDetailPage) },
          { path: 'compras/ordenes/:id/editar', element: page(ComprasOrdenesCreatePage) },
          { path: 'compras/documentos', element: page(ComprasDocumentosListPage) },
          { path: 'compras/documentos/nuevo', element: page(ComprasDocumentosCreatePage) },
          { path: 'compras/documentos/:id', element: page(ComprasDocumentosDetailPage) },
          { path: 'compras/documentos/:id/editar', element: page(ComprasDocumentosCreatePage) },
          { path: 'compras/recepciones', element: page(ComprasRecepcionesListPage) },
          { path: 'compras/recepciones/nuevo', element: page(ComprasRecepcionesCreatePage) },
          { path: 'compras/recepciones/:id/editar', element: page(ComprasRecepcionesCreatePage) },
          { path: 'contabilidad/plan-cuentas', element: page(ContabilidadPlanPage) },
          { path: 'contabilidad/asientos', element: page(ContabilidadAsientosPage) },
          { path: 'contabilidad/asientos/:id', element: page(ContabilidadAsientoDetailPage) },
          { path: 'contabilidad/reportes', element: page(ContabilidadReportesPage) },
          { path: 'auditoria/eventos', element: page(AuditoriaEventosPage) },
          { path: 'auditoria/eventos/:id', element: page(AuditoriaEventoDetailPage) },
          { path: 'administracion/permisos', element: page(AdministracionPermisosPage) },
          { path: 'administracion/sii', element: page(AdministracionSiiPage) },
          { path: 'contabilidad/sii', element: page(AdministracionSiiPage) },
          { path: 'inventario/bodegas', element: page(InventarioBodegasPage) },
          { path: 'inventario/kardex', element: page(InventarioKardexPage) },
          { path: 'inventario/resumen', element: page(InventarioResumenPage) },
          { path: 'tesoreria/bancos', element: page(TesoreriaBancosPage) },
          { path: 'tesoreria/cartera', element: page(TesoreriaCuentasPage) },
          { path: 'tesoreria/monedas', element: page(TesoreriaMonedasPage) },
          { path: 'tesoreria/tipos-cambio', element: page(TesoreriaTipoCambioPage) },
          { path: 'ventas/pedidos', element: page(VentasPedidosListPage) },
          { path: 'ventas/pedidos/nuevo', element: page(VentasPedidosFormPage) },
          { path: 'ventas/pedidos/:id', element: page(VentasPedidosDetailPage) },
          { path: 'ventas/pedidos/:id/editar', element: page(VentasPedidosFormPage) },
          { path: 'ventas/guias', element: page(VentasGuiasListPage) },
          { path: 'ventas/guias/nuevo', element: page(VentasGuiasFormPage) },
          { path: 'ventas/guias/:id/editar', element: page(VentasGuiasFormPage) },
          { path: 'ventas/facturas', element: page(VentasFacturasListPage) },
          { path: 'ventas/facturas/nuevo', element: page(VentasFacturasFormPage) },
          { path: 'ventas/facturas/:id/editar', element: page(VentasFacturasFormPage) },
          { path: 'ventas/notas', element: page(VentasNotasListPage) },
          { path: 'ventas/notas/nuevo', element: page(VentasNotasFormPage) },
          { path: 'ventas/notas/:id/editar', element: page(VentasNotasFormPage) },
        ],
      },
    ],
  },
  {
    element: <PublicOnlyRoute />,
    children: [
      {
        path: '/auth/login',
        element: page(LoginPage),
      },
    ],
  },
  {
    path: '*',
    element: page(NotFoundPage),
  },
])

export default router

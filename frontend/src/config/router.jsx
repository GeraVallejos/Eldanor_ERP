import { Suspense, lazy } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import ERPLayout from '@/layouts/ERPLayout'
import { PRODUCTOS_MANAGE_ANY } from '@/config/productosAccess'
import PrivateRoute from '@/modules/auth/components/PrivateRoute'
import PublicOnlyRoute from '@/modules/auth/components/PublicOnlyRoute'
import PermissionRoute from '@/modules/shared/auth/PermissionRoute'

const LoginPage = lazy(() => import('@/modules/auth/pages/LoginPage'))
const HomeRedirectPage = lazy(() => import('@/modules/shared/pages/HomeRedirectPage'))
const ClientesCreatePage = lazy(() => import('@/modules/contactos/pages/ClientesCreatePage'))
const ClientesListPage = lazy(() => import('@/modules/contactos/pages/ClientesListPage'))
const ProveedoresCreatePage = lazy(() => import('@/modules/contactos/pages/ProveedoresCreatePage'))
const ProveedoresListPage = lazy(() => import('@/modules/contactos/pages/ProveedoresListPage'))
const PresupuestosCreatePage = lazy(() => import('@/modules/presupuestos/pages/PresupuestosCreatePage'))
const PresupuestosEditPage = lazy(() => import('@/modules/presupuestos/pages/PresupuestosEditPage'))
const PresupuestosListPage = lazy(() => import('@/modules/presupuestos/pages/PresupuestosListPage'))
const PresupuestoTrazabilidadPage = lazy(() => import('@/modules/presupuestos/pages/PresupuestoTrazabilidadPage'))
const ComprasOrdenesListPage = lazy(() => import('@/modules/compras/pages/ComprasOrdenesListPage'))
const ComprasResumenPage = lazy(() => import('@/modules/compras/pages/ComprasResumenPage'))
const ComprasReportesPage = lazy(() => import('@/modules/compras/pages/ComprasReportesPage'))
const ComprasOrdenesCreatePage = lazy(() => import('@/modules/compras/pages/ComprasOrdenesCreatePage'))
const ComprasOrdenesDetailPage = lazy(() => import('@/modules/compras/pages/ComprasOrdenesDetailPage'))
const ComprasTrazabilidadPage = lazy(() => import('@/modules/compras/pages/ComprasTrazabilidadPage'))
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
const FacturacionSiiPage = lazy(() => import('@/modules/facturacion/pages/FacturacionSiiPage'))
const InventarioAjustesPage = lazy(() => import('@/modules/inventario/pages/InventarioAjustesPage'))
const InventarioBodegasPage = lazy(() => import('@/modules/inventario/pages/InventarioBodegasPage'))
const InventarioKardexPage = lazy(() => import('@/modules/inventario/pages/InventarioKardexPage'))
const InventarioReportesPage = lazy(() => import('@/modules/inventario/pages/InventarioReportesPage'))
const InventarioResumenPage = lazy(() => import('@/modules/inventario/pages/InventarioResumenPage'))
const InventarioTrasladosPage = lazy(() => import('@/modules/inventario/pages/InventarioTrasladosPage'))
const TesoreriaBancosPage = lazy(() => import('@/modules/tesoreria/pages/TesoreriaBancosPage'))
const TesoreriaCuentasPage = lazy(() => import('@/modules/tesoreria/pages/TesoreriaCuentasPage'))
const TesoreriaMonedasPage = lazy(() => import('@/modules/tesoreria/pages/TesoreriaMonedasPage'))
const TesoreriaTipoCambioPage = lazy(() => import('@/modules/tesoreria/pages/TesoreriaTipoCambioPage'))
const VentasPedidosListPage = lazy(() => import('@/modules/ventas/pages/VentasPedidosListPage'))
const VentasPedidosFormPage = lazy(() => import('@/modules/ventas/pages/VentasPedidosFormPage'))
const VentasPedidosDetailPage = lazy(() => import('@/modules/ventas/pages/VentasPedidosDetailPage'))
const VentasResumenPage = lazy(() => import('@/modules/ventas/pages/VentasResumenPage'))
const VentasReportesPage = lazy(() => import('@/modules/ventas/pages/VentasReportesPage'))
const VentasGuiasListPage = lazy(() => import('@/modules/ventas/pages/VentasGuiasListPage'))
const VentasGuiasFormPage = lazy(() => import('@/modules/ventas/pages/VentasGuiasFormPage'))
const VentasFacturasListPage = lazy(() => import('@/modules/ventas/pages/VentasFacturasListPage'))
const VentasFacturasFormPage = lazy(() => import('@/modules/ventas/pages/VentasFacturasFormPage'))
const VentasNotasListPage = lazy(() => import('@/modules/ventas/pages/VentasNotasListPage'))
const VentasNotasFormPage = lazy(() => import('@/modules/ventas/pages/VentasNotasFormPage'))
const ProductosCreatePage = lazy(() => import('@/modules/productos/pages/ProductosCreatePage'))
const ProductosCategoriasPage = lazy(() => import('@/modules/productos/pages/ProductosCategoriasPage'))
const ProductosAnalisisPage = lazy(() => import('@/modules/productos/pages/ProductosAnalisisPage'))
const ProductosDetailPage = lazy(() => import('@/modules/productos/pages/ProductosDetailPage'))
const ProductosImpuestosPage = lazy(() => import('@/modules/productos/pages/ProductosImpuestosPage'))
const ProductosListaPrecioDetailPage = lazy(() => import('@/modules/productos/pages/ProductosListaPrecioDetailPage'))
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

function guardedPage(LazyPage, permission, message, options = {}) {
  return (
    <PermissionRoute permission={permission} message={message} requireAny={Boolean(options.requireAny)}>
      {page(LazyPage)}
    </PermissionRoute>
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
          { index: true, element: page(HomeRedirectPage) },
          { path: 'contactos', element: guardedPage(ClientesListPage, 'CONTACTOS.VER', 'No tiene permiso para revisar contactos.') },
          { path: 'contactos/clientes', element: guardedPage(ClientesListPage, 'CONTACTOS.VER', 'No tiene permiso para revisar clientes.') },
          { path: 'contactos/clientes/nuevo', element: guardedPage(ClientesCreatePage, 'CONTACTOS.CREAR', 'No tiene permiso para crear clientes.') },
          { path: 'contactos/proveedores', element: guardedPage(ProveedoresListPage, 'CONTACTOS.VER', 'No tiene permiso para revisar proveedores.') },
          { path: 'contactos/proveedores/nuevo', element: guardedPage(ProveedoresCreatePage, 'CONTACTOS.CREAR', 'No tiene permiso para crear proveedores.') },
          { path: 'presupuestos', element: guardedPage(PresupuestosListPage, 'PRESUPUESTOS.VER', 'No tiene permiso para revisar presupuestos.') },
          { path: 'presupuestos/nuevo', element: guardedPage(PresupuestosCreatePage, 'PRESUPUESTOS.CREAR', 'No tiene permiso para crear presupuestos.') },
          { path: 'presupuestos/:id/editar', element: guardedPage(PresupuestosEditPage, 'PRESUPUESTOS.EDITAR', 'No tiene permiso para editar presupuestos.') },
          { path: 'presupuestos/:id/trazabilidad', element: guardedPage(PresupuestoTrazabilidadPage, 'PRESUPUESTOS.VER', 'No tiene permiso para revisar la trazabilidad del presupuesto.') },
          { path: 'productos', element: guardedPage(ProductosListPage, 'PRODUCTOS.VER', 'No tiene permiso para revisar productos.') },
          { path: 'productos/:id', element: guardedPage(ProductosDetailPage, 'PRODUCTOS.VER', 'No tiene permiso para revisar el detalle del producto.') },
          { path: 'productos/:id/analisis', element: guardedPage(ProductosAnalisisPage, 'PRODUCTOS.VER', 'No tiene permiso para revisar el analisis del producto.') },
          { path: 'productos/nuevo', element: guardedPage(ProductosCreatePage, 'PRODUCTOS.CREAR', 'No tiene permiso para crear productos.') },
          { path: 'productos/:id/editar', element: guardedPage(ProductosCreatePage, 'PRODUCTOS.EDITAR', 'No tiene permiso para editar productos.') },
          {
            path: 'productos/categorias',
            element: guardedPage(
              ProductosCategoriasPage,
              PRODUCTOS_MANAGE_ANY,
              'No tiene permiso para gestionar categorias.',
              { requireAny: true },
            ),
          },
          {
            path: 'productos/impuestos',
            element: guardedPage(
              ProductosImpuestosPage,
              PRODUCTOS_MANAGE_ANY,
              'No tiene permiso para gestionar impuestos.',
              { requireAny: true },
            ),
          },
          {
            path: 'productos/listas-precio',
            element: guardedPage(
              ProductosListasPrecioPage,
              PRODUCTOS_MANAGE_ANY,
              'No tiene permiso para gestionar listas de precio.',
              { requireAny: true },
            ),
          },
          {
            path: 'productos/listas-precio/:id',
            element: guardedPage(
              ProductosListaPrecioDetailPage,
              PRODUCTOS_MANAGE_ANY,
              'No tiene permiso para gestionar precios de la lista.',
              { requireAny: true },
            ),
          },
          { path: 'compras/ordenes', element: guardedPage(ComprasOrdenesListPage, 'COMPRAS.VER', 'No tiene permiso para revisar ordenes de compra.') },
          { path: 'compras/resumen', element: guardedPage(ComprasResumenPage, 'COMPRAS.VER', 'No tiene permiso para revisar el resumen de compras.') },
          { path: 'compras/reportes', element: guardedPage(ComprasReportesPage, 'COMPRAS.VER', 'No tiene permiso para revisar reportes de compras.') },
          { path: 'compras/ordenes/nuevo', element: guardedPage(ComprasOrdenesCreatePage, 'COMPRAS.CREAR', 'No tiene permiso para crear ordenes de compra.') },
          { path: 'compras/ordenes/:id', element: guardedPage(ComprasOrdenesDetailPage, 'COMPRAS.VER', 'No tiene permiso para revisar el detalle de la orden de compra.') },
          { path: 'compras/ordenes/:id/trazabilidad', element: guardedPage(ComprasTrazabilidadPage, 'COMPRAS.VER', 'No tiene permiso para revisar la trazabilidad de compras.') },
          { path: 'compras/ordenes/:id/editar', element: guardedPage(ComprasOrdenesCreatePage, 'COMPRAS.EDITAR', 'No tiene permiso para editar ordenes de compra.') },
          { path: 'compras/documentos', element: guardedPage(ComprasDocumentosListPage, 'COMPRAS.VER', 'No tiene permiso para revisar documentos de compra.') },
          { path: 'compras/documentos/nuevo', element: guardedPage(ComprasDocumentosCreatePage, 'COMPRAS.CREAR', 'No tiene permiso para crear documentos de compra.') },
          { path: 'compras/documentos/:id', element: guardedPage(ComprasDocumentosDetailPage, 'COMPRAS.VER', 'No tiene permiso para revisar el detalle del documento de compra.') },
          { path: 'compras/documentos/:id/editar', element: guardedPage(ComprasDocumentosCreatePage, 'COMPRAS.EDITAR', 'No tiene permiso para editar documentos de compra.') },
          { path: 'compras/recepciones', element: guardedPage(ComprasRecepcionesListPage, 'COMPRAS.VER', 'No tiene permiso para revisar recepciones de compra.') },
          { path: 'compras/recepciones/nuevo', element: guardedPage(ComprasRecepcionesCreatePage, 'COMPRAS.CREAR', 'No tiene permiso para crear recepciones de compra.') },
          { path: 'compras/recepciones/:id/editar', element: guardedPage(ComprasRecepcionesCreatePage, 'COMPRAS.EDITAR', 'No tiene permiso para editar recepciones de compra.') },
          { path: 'contabilidad/plan-cuentas', element: guardedPage(ContabilidadPlanPage, 'CONTABILIDAD.VER', 'No tiene permiso para revisar el plan de cuentas.') },
          { path: 'contabilidad/asientos', element: guardedPage(ContabilidadAsientosPage, 'CONTABILIDAD.VER', 'No tiene permiso para revisar asientos contables.') },
          { path: 'contabilidad/asientos/:id', element: guardedPage(ContabilidadAsientoDetailPage, 'CONTABILIDAD.VER', 'No tiene permiso para revisar el detalle contable.') },
          { path: 'contabilidad/reportes', element: guardedPage(ContabilidadReportesPage, 'CONTABILIDAD.VER', 'No tiene permiso para revisar reportes contables.') },
          { path: 'auditoria/eventos', element: guardedPage(AuditoriaEventosPage, 'AUDITORIA.VER', 'No tiene permiso para revisar auditoria.') },
          { path: 'auditoria/eventos/:id', element: guardedPage(AuditoriaEventoDetailPage, 'AUDITORIA.VER', 'No tiene permiso para revisar el detalle de auditoria.') },
          { path: 'administracion/permisos', element: guardedPage(AdministracionPermisosPage, 'ADMINISTRACION.GESTIONAR_PERMISOS', 'No tiene permiso para gestionar permisos.') },
          { path: 'facturacion/sii', element: guardedPage(FacturacionSiiPage, 'FACTURACION.VER', 'No tiene permiso para revisar configuracion de facturacion.') },
          { path: 'administracion/sii', element: guardedPage(FacturacionSiiPage, 'FACTURACION.VER', 'No tiene permiso para revisar configuracion SII.') },
          { path: 'contabilidad/sii', element: guardedPage(FacturacionSiiPage, 'FACTURACION.VER', 'No tiene permiso para revisar configuracion SII.') },
          { path: 'inventario/ajustes', element: guardedPage(InventarioAjustesPage, 'INVENTARIO.EDITAR', 'No tiene permiso para gestionar ajustes de inventario.') },
          { path: 'inventario/bodegas', element: guardedPage(InventarioBodegasPage, 'INVENTARIO.VER', 'No tiene permiso para revisar bodegas.') },
          { path: 'inventario/kardex', element: guardedPage(InventarioKardexPage, 'INVENTARIO.VER', 'No tiene permiso para revisar kardex.') },
          { path: 'inventario/reportes', element: guardedPage(InventarioReportesPage, 'INVENTARIO.VER', 'No tiene permiso para revisar reportes de inventario.') },
          { path: 'inventario/resumen', element: guardedPage(InventarioResumenPage, 'INVENTARIO.VER', 'No tiene permiso para revisar el resumen de inventario.') },
          { path: 'inventario/traslados', element: guardedPage(InventarioTrasladosPage, 'INVENTARIO.EDITAR', 'No tiene permiso para gestionar traslados de inventario.') },
          { path: 'tesoreria/bancos', element: guardedPage(TesoreriaBancosPage, 'TESORERIA.VER', 'No tiene permiso para revisar tesoreria bancaria.') },
          { path: 'tesoreria/cartera', element: guardedPage(TesoreriaCuentasPage, 'TESORERIA.VER', 'No tiene permiso para ver tesoreria.') },
          { path: 'tesoreria/monedas', element: guardedPage(TesoreriaMonedasPage, 'TESORERIA.VER', 'No tiene permiso para revisar monedas.') },
          { path: 'tesoreria/tipos-cambio', element: guardedPage(TesoreriaTipoCambioPage, 'TESORERIA.VER', 'No tiene permiso para revisar tipos de cambio.') },
          { path: 'ventas/pedidos', element: guardedPage(VentasPedidosListPage, 'VENTAS.VER', 'No tiene permiso para revisar pedidos de venta.') },
          { path: 'ventas/resumen', element: guardedPage(VentasResumenPage, 'VENTAS.VER', 'No tiene permiso para revisar el resumen de ventas.') },
          { path: 'ventas/reportes', element: guardedPage(VentasReportesPage, 'VENTAS.VER', 'No tiene permiso para revisar reportes de ventas.') },
          { path: 'ventas/pedidos/nuevo', element: guardedPage(VentasPedidosFormPage, 'VENTAS.CREAR', 'No tiene permiso para crear pedidos de venta.') },
          { path: 'ventas/pedidos/:id', element: guardedPage(VentasPedidosDetailPage, 'VENTAS.VER', 'No tiene permiso para revisar el detalle del pedido de venta.') },
          { path: 'ventas/pedidos/:id/editar', element: guardedPage(VentasPedidosFormPage, 'VENTAS.EDITAR', 'No tiene permiso para editar pedidos de venta.') },
          { path: 'ventas/guias', element: guardedPage(VentasGuiasListPage, 'VENTAS.VER', 'No tiene permiso para revisar guias de despacho.') },
          { path: 'ventas/guias/nuevo', element: guardedPage(VentasGuiasFormPage, 'VENTAS.CREAR', 'No tiene permiso para crear guias de despacho.') },
          { path: 'ventas/guias/:id/editar', element: guardedPage(VentasGuiasFormPage, 'VENTAS.EDITAR', 'No tiene permiso para editar guias de despacho.') },
          { path: 'ventas/facturas', element: guardedPage(VentasFacturasListPage, 'VENTAS.VER', 'No tiene permiso para revisar facturas de venta.') },
          { path: 'ventas/facturas/nuevo', element: guardedPage(VentasFacturasFormPage, 'VENTAS.CREAR', 'No tiene permiso para crear facturas de venta.') },
          { path: 'ventas/facturas/:id/editar', element: guardedPage(VentasFacturasFormPage, 'VENTAS.EDITAR', 'No tiene permiso para editar facturas de venta.') },
          { path: 'ventas/notas', element: guardedPage(VentasNotasListPage, 'VENTAS.VER', 'No tiene permiso para revisar notas de credito.') },
          { path: 'ventas/notas/nuevo', element: guardedPage(VentasNotasFormPage, 'VENTAS.CREAR', 'No tiene permiso para crear notas de credito.') },
          { path: 'ventas/notas/:id/editar', element: guardedPage(VentasNotasFormPage, 'VENTAS.EDITAR', 'No tiene permiso para editar notas de credito.') },
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

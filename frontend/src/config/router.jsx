import { createBrowserRouter } from 'react-router-dom'
import ERPLayout from '@/layouts/ERPLayout'
import PrivateRoute from '@/modules/auth/components/PrivateRoute'
import PublicOnlyRoute from '@/modules/auth/components/PublicOnlyRoute'
import LoginPage from '@/modules/auth/pages/LoginPage'
import ClientesCreatePage from '@/modules/contactos/pages/ClientesCreatePage'
import ClientesListPage from '@/modules/contactos/pages/ClientesListPage'
import ProveedoresCreatePage from '@/modules/contactos/pages/ProveedoresCreatePage'
import ProveedoresListPage from '@/modules/contactos/pages/ProveedoresListPage'
import PresupuestosCreatePage from '@/modules/presupuestos/pages/PresupuestosCreatePage'
import PresupuestosEditPage from '@/modules/presupuestos/pages/PresupuestosEditPage'
import PresupuestosListPage from '@/modules/presupuestos/pages/PresupuestosListPage'
import ComprasOrdenesListPage from '@/modules/compras/pages/ComprasOrdenesListPage'
import ComprasOrdenesCreatePage from '@/modules/compras/pages/ComprasOrdenesCreatePage'
import ComprasOrdenesDetailPage from '@/modules/compras/pages/ComprasOrdenesDetailPage'
import ComprasDocumentosListPage from '@/modules/compras/pages/ComprasDocumentosListPage'
import ComprasDocumentosCreatePage from '@/modules/compras/pages/ComprasDocumentosCreatePage'
import ComprasDocumentosDetailPage from '@/modules/compras/pages/ComprasDocumentosDetailPage'
import ComprasRecepcionesListPage from '@/modules/compras/pages/ComprasRecepcionesListPage'
import ComprasRecepcionesCreatePage from '@/modules/compras/pages/ComprasRecepcionesCreatePage'
import ContabilidadAsientosPage from '@/modules/contabilidad/pages/ContabilidadAsientosPage'
import ContabilidadPlanPage from '@/modules/contabilidad/pages/ContabilidadPlanPage'
import AuditoriaEventosPage from '@/modules/auditoria/pages/AuditoriaEventosPage'
import AuditoriaEventoDetailPage from '@/modules/auditoria/pages/AuditoriaEventoDetailPage'
import AdministracionPermisosPage from '@/modules/administracion/pages/AdministracionPermisosPage'
import AdministracionSiiPage from '@/modules/administracion/pages/AdministracionSiiPage'
import InventarioBodegasPage from '@/modules/inventario/pages/InventarioBodegasPage'
import InventarioKardexPage from '@/modules/inventario/pages/InventarioKardexPage'
import InventarioResumenPage from '@/modules/inventario/pages/InventarioResumenPage'
import TesoreriaBancosPage from '@/modules/tesoreria/pages/TesoreriaBancosPage'
import TesoreriaCuentasPage from '@/modules/tesoreria/pages/TesoreriaCuentasPage'
import TesoreriaMonedasPage from '@/modules/tesoreria/pages/TesoreriaMonedasPage'
import TesoreriaTipoCambioPage from '@/modules/tesoreria/pages/TesoreriaTipoCambioPage'
import VentasPedidosListPage from '@/modules/ventas/pages/VentasPedidosListPage'
import VentasPedidosFormPage from '@/modules/ventas/pages/VentasPedidosFormPage'
import VentasPedidosDetailPage from '@/modules/ventas/pages/VentasPedidosDetailPage'
import VentasGuiasListPage from '@/modules/ventas/pages/VentasGuiasListPage'
import VentasGuiasFormPage from '@/modules/ventas/pages/VentasGuiasFormPage'
import VentasFacturasListPage from '@/modules/ventas/pages/VentasFacturasListPage'
import VentasFacturasFormPage from '@/modules/ventas/pages/VentasFacturasFormPage'
import VentasNotasListPage from '@/modules/ventas/pages/VentasNotasListPage'
import VentasNotasFormPage from '@/modules/ventas/pages/VentasNotasFormPage'
import ProductosCreatePage from '@/modules/productos/pages/ProductosCreatePage'
import ProductosCategoriasPage from '@/modules/productos/pages/ProductosCategoriasPage'
import ProductosImpuestosPage from '@/modules/productos/pages/ProductosImpuestosPage'
import ProductosListasPrecioPage from '@/modules/productos/pages/ProductosListasPrecioPage'
import ProductosListPage from '@/modules/productos/pages/ProductosListPage'
import NotFoundPage from '@/modules/shared/pages/NotFoundPage'

const router = createBrowserRouter([
  {
    element: <PrivateRoute />,
    children: [
      {
        path: '/',
        element: <ERPLayout />,
        children: [
          { index: true, element: <ProductosListPage /> },
          { path: 'contactos', element: <ClientesListPage /> },
          { path: 'contactos/clientes', element: <ClientesListPage /> },
          { path: 'contactos/clientes/nuevo', element: <ClientesCreatePage /> },
          { path: 'contactos/proveedores', element: <ProveedoresListPage /> },
          { path: 'contactos/proveedores/nuevo', element: <ProveedoresCreatePage /> },
          { path: 'presupuestos', element: <PresupuestosListPage /> },
          { path: 'presupuestos/nuevo', element: <PresupuestosCreatePage /> },
          { path: 'presupuestos/:id/editar', element: <PresupuestosEditPage /> },
          { path: 'productos', element: <ProductosListPage /> },
          { path: 'productos/nuevo', element: <ProductosCreatePage /> },
          { path: 'productos/categorias', element: <ProductosCategoriasPage /> },
          { path: 'productos/impuestos', element: <ProductosImpuestosPage /> },
          { path: 'productos/listas-precio', element: <ProductosListasPrecioPage /> },
          { path: 'compras/ordenes', element: <ComprasOrdenesListPage /> },
          { path: 'compras/ordenes/nuevo', element: <ComprasOrdenesCreatePage /> },
          { path: 'compras/ordenes/:id', element: <ComprasOrdenesDetailPage /> },
          { path: 'compras/ordenes/:id/editar', element: <ComprasOrdenesCreatePage /> },
          { path: 'compras/documentos', element: <ComprasDocumentosListPage /> },
          { path: 'compras/documentos/nuevo', element: <ComprasDocumentosCreatePage /> },
          { path: 'compras/documentos/:id', element: <ComprasDocumentosDetailPage /> },
          { path: 'compras/documentos/:id/editar', element: <ComprasDocumentosCreatePage /> },
          { path: 'compras/recepciones', element: <ComprasRecepcionesListPage /> },
          { path: 'compras/recepciones/nuevo', element: <ComprasRecepcionesCreatePage /> },
          { path: 'compras/recepciones/:id/editar', element: <ComprasRecepcionesCreatePage /> },
          { path: 'contabilidad/plan-cuentas', element: <ContabilidadPlanPage /> },
          { path: 'contabilidad/asientos', element: <ContabilidadAsientosPage /> },
          { path: 'auditoria/eventos', element: <AuditoriaEventosPage /> },
          { path: 'auditoria/eventos/:id', element: <AuditoriaEventoDetailPage /> },
          { path: 'administracion/permisos', element: <AdministracionPermisosPage /> },
          { path: 'administracion/sii', element: <AdministracionSiiPage /> },
          { path: 'contabilidad/sii', element: <AdministracionSiiPage /> },
          { path: 'inventario/bodegas', element: <InventarioBodegasPage /> },
          { path: 'inventario/kardex', element: <InventarioKardexPage /> },
          { path: 'inventario/resumen', element: <InventarioResumenPage /> },
          { path: 'tesoreria/bancos', element: <TesoreriaBancosPage /> },
          { path: 'tesoreria/cartera', element: <TesoreriaCuentasPage /> },
          { path: 'tesoreria/monedas', element: <TesoreriaMonedasPage /> },
          { path: 'tesoreria/tipos-cambio', element: <TesoreriaTipoCambioPage /> },
          { path: 'ventas/pedidos', element: <VentasPedidosListPage /> },
          { path: 'ventas/pedidos/nuevo', element: <VentasPedidosFormPage /> },
          { path: 'ventas/pedidos/:id', element: <VentasPedidosDetailPage /> },
          { path: 'ventas/pedidos/:id/editar', element: <VentasPedidosFormPage /> },
          { path: 'ventas/guias', element: <VentasGuiasListPage /> },
          { path: 'ventas/guias/nuevo', element: <VentasGuiasFormPage /> },
          { path: 'ventas/guias/:id/editar', element: <VentasGuiasFormPage /> },
          { path: 'ventas/facturas', element: <VentasFacturasListPage /> },
          { path: 'ventas/facturas/nuevo', element: <VentasFacturasFormPage /> },
          { path: 'ventas/facturas/:id/editar', element: <VentasFacturasFormPage /> },
          { path: 'ventas/notas', element: <VentasNotasListPage /> },
          { path: 'ventas/notas/nuevo', element: <VentasNotasFormPage /> },
          { path: 'ventas/notas/:id/editar', element: <VentasNotasFormPage /> },
        ],
      },
    ],
  },
  {
    element: <PublicOnlyRoute />,
    children: [
      {
        path: '/auth/login',
        element: <LoginPage />,
      },
    ],
  },
  {
    path: '*',
    element: <NotFoundPage />,
  },
])

export default router

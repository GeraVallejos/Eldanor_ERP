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
import ProductosCreatePage from '@/modules/productos/pages/ProductosCreatePage'
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

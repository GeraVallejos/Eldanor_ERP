import { createBrowserRouter } from 'react-router-dom'
import ERPLayout from '@/layouts/ERPLayout'
import PrivateRoute from '@/modules/auth/components/PrivateRoute'
import PublicOnlyRoute from '@/modules/auth/components/PublicOnlyRoute'
import LoginPage from '@/modules/auth/pages/LoginPage'
import ContactosPage from '@/modules/contactos/pages/ContactosPage'
import PresupuestosPage from '@/modules/presupuestos/pages/PresupuestosPage'
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
          { path: 'contactos', element: <ContactosPage /> },
          { path: 'presupuestos', element: <PresupuestosPage /> },
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

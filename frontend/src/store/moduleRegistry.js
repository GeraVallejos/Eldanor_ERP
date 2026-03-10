import { authStoreModule } from '@/modules/auth/store'
import { productosStoreModule } from '@/modules/productos/store'
import { comprasStoreModule } from '@/modules/compras/store'
import { inventarioStoreModule } from '@/modules/inventario/store'
import { contactosStoreModule } from '@/modules/contactos/store'
import { presupuestosStoreModule } from '@/modules/presupuestos/store'

export const STORE_MODULES = [
  authStoreModule,
  productosStoreModule,
  comprasStoreModule,
  inventarioStoreModule,
  contactosStoreModule,
  presupuestosStoreModule,
]

export function buildReducersFromModules(modules = STORE_MODULES) {
  return modules.reduce((acc, moduleConfig) => {
    acc[moduleConfig.key] = moduleConfig.reducer
    return acc
  }, {})
}

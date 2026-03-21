import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { useDispatch, useSelector } from 'react-redux'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { z } from 'zod'
import ApiContractError from '@/components/ui/ApiContractError'
import Button from '@/components/ui/Button'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { cn } from '@/lib/utils'
import { invalidateProductosCatalogCache } from '@/modules/productos/services/productosCatalogCache'
import {
  createProducto,
  fetchCatalogosProducto,
  fetchProductos,
  resetCreateProductoState,
  selectCatalogError,
  selectCatalogStatus,
  selectCategorias,
  selectCreateProductoError,
  selectCreateProductoStatus,
  selectImpuestos,
} from '@/modules/productos/productosSlice'

const tipoProductoValues = ['PRODUCTO', 'SERVICIO']

const productoSchema = z
  .object({
    nombre: z.string().trim().min(2, 'Nombre requerido (minimo 2 caracteres).'),
    descripcion: z.string().max(500, 'Descripcion demasiado larga.').optional(),
    sku: z.string().trim().min(1, 'SKU requerido.').max(100, 'SKU demasiado largo.'),
    tipo: z.enum(tipoProductoValues),
    categoria: z.string().optional(),
    impuesto: z.string().optional(),
    precio_referencia: z.number({ error: 'Precio de referencia invalido.' }).min(0, 'No puede ser negativo.'),
    precio_costo: z.number({ error: 'Precio de costo invalido.' }).min(0, 'No puede ser negativo.'),
    maneja_inventario: z.boolean(),
    stock_actual: z.number({ error: 'Stock invalido.' }).min(0, 'No puede ser negativo.'),
    activo: z.boolean(),
  })
  .superRefine((values, ctx) => {
    if (values.tipo === 'SERVICIO') {
      if (values.maneja_inventario) {
        ctx.addIssue({
          code: 'custom',
          path: ['maneja_inventario'],
          message: 'Un servicio no maneja inventario.',
        })
      }

      if (values.stock_actual !== 0) {
        ctx.addIssue({
          code: 'custom',
          path: ['stock_actual'],
          message: 'El stock de un servicio debe ser 0.',
        })
      }
    }
  })

function ProductosCreatePage() {
  const dispatch = useDispatch()
  const categorias = useSelector(selectCategorias)
  const impuestos = useSelector(selectImpuestos)
  const catalogStatus = useSelector(selectCatalogStatus)
  const catalogError = useSelector(selectCatalogError)
  const createStatus = useSelector(selectCreateProductoStatus)
  const createError = useSelector(selectCreateProductoError)

  const {
    register,
    handleSubmit,
    control,
    reset,
    setValue,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(productoSchema),
    defaultValues: {
      nombre: '',
      descripcion: '',
      sku: '',
      tipo: 'PRODUCTO',
      categoria: '',
      impuesto: '',
      precio_referencia: 0,
      precio_costo: 0,
      maneja_inventario: true,
      stock_actual: 0,
      activo: true,
    },
  })

  const tipoSeleccionado = useWatch({ control, name: 'tipo' })

  useEffect(() => {
    if (catalogStatus === 'idle') {
      dispatch(fetchCatalogosProducto())
    }
  }, [catalogStatus, dispatch])

  useEffect(() => {
    if (tipoSeleccionado === 'SERVICIO') {
      setValue('maneja_inventario', false, { shouldValidate: true })
      setValue('stock_actual', 0, { shouldValidate: true })
      return
    }

    if (tipoSeleccionado === 'PRODUCTO') {
      setValue('maneja_inventario', true, { shouldValidate: true })
    }
  }, [setValue, tipoSeleccionado])

  useEffect(() => {
    if (catalogStatus === 'failed' && catalogError) {
      toast.error(catalogError)
    }
  }, [catalogError, catalogStatus])

  useEffect(() => {
    return () => {
      dispatch(resetCreateProductoState())
    }
  }, [dispatch])

  const onSubmit = async (values) => {
    dispatch(resetCreateProductoState())

    const payload = {
      ...values,
      categoria: values.categoria || null,
      impuesto: values.impuesto || null,
      descripcion: values.descripcion?.trim() || '',
      maneja_inventario: values.tipo === 'SERVICIO' ? false : values.maneja_inventario,
      stock_actual: values.tipo === 'SERVICIO' ? 0 : values.stock_actual,
    }

    try {
      await dispatch(createProducto(payload)).unwrap()
      invalidateProductosCatalogCache()
      toast.success('Producto creado correctamente.')
      reset({
        nombre: '',
        descripcion: '',
        sku: '',
        tipo: 'PRODUCTO',
        categoria: '',
        impuesto: '',
        precio_referencia: 0,
        precio_costo: 0,
        maneja_inventario: true,
        stock_actual: 0,
        activo: true,
      })
      dispatch(fetchProductos())
      dispatch(resetCreateProductoState())
    } catch (error) {
      toast.error(typeof error === 'string' ? error : (error?.message || 'No se pudo crear el producto.'))
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Nuevo producto</h2>
          <p className="text-sm text-muted-foreground">Formulario seguro para alta de productos.</p>
        </div>
        <Link
          to="/productos"
          className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}
        >
          Volver al listado
        </Link>
      </div>

      <form className="rounded-md border border-border bg-card p-4" onSubmit={handleSubmit(onSubmit)}>
        <ApiContractError
          error={typeof createError === 'object' ? createError : null}
          title="No se pudo crear el producto."
        />
        <div className="grid gap-3 md:grid-cols-2">
          <label className="text-sm">
            Nombre
            <input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" {...register('nombre')} />
            {errors.nombre && <span className="mt-1 block text-xs text-destructive">{errors.nombre.message}</span>}
          </label>

          <label className="text-sm">
            SKU
            <input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" {...register('sku')} />
            {errors.sku && <span className="mt-1 block text-xs text-destructive">{errors.sku.message}</span>}
          </label>

          <label className="text-sm md:col-span-2">
            Descripcion
            <textarea className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" rows={3} {...register('descripcion')} />
            {errors.descripcion && <span className="mt-1 block text-xs text-destructive">{errors.descripcion.message}</span>}
          </label>

          <label className="text-sm">
            Tipo
            <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" {...register('tipo')}>
              <option value="PRODUCTO">Producto</option>
              <option value="SERVICIO">Servicio</option>
            </select>
          </label>

          <label className="text-sm">
            Categoria
            <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" disabled={catalogStatus === 'loading'} {...register('categoria')}>
              <option value="">Sin categoria</option>
              {categorias.map((categoria) => (
                <option key={categoria.id} value={categoria.id}>{categoria.nombre}</option>
              ))}
            </select>
          </label>

          <label className="text-sm">
            Impuesto
            <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" disabled={catalogStatus === 'loading'} {...register('impuesto')}>
              <option value="">Sin impuesto</option>
              {impuestos.map((impuesto) => (
                <option key={impuesto.id} value={impuesto.id}>{impuesto.nombre}</option>
              ))}
            </select>
          </label>

          <label className="text-sm">
            Precio referencia
            <input type="number" step="1" min="0" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" {...register('precio_referencia', { valueAsNumber: true })} />
            {errors.precio_referencia && <span className="mt-1 block text-xs text-destructive">{errors.precio_referencia.message}</span>}
          </label>

          <label className="text-sm">
            Precio costo
            <input type="number" step="1" min="0" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" {...register('precio_costo', { valueAsNumber: true })} />
            {errors.precio_costo && <span className="mt-1 block text-xs text-destructive">{errors.precio_costo.message}</span>}
          </label>

          <label className="text-sm">
            Stock actual
            <input type="number" step="0.01" min="0" disabled={tipoSeleccionado === 'SERVICIO'} className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 disabled:opacity-60" {...register('stock_actual', { valueAsNumber: true })} />
            {errors.stock_actual && <span className="mt-1 block text-xs text-destructive">{errors.stock_actual.message}</span>}
          </label>

          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" disabled={tipoSeleccionado === 'SERVICIO'} {...register('maneja_inventario')} />
            Maneja inventario
          </label>

          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" {...register('activo')} />
            Activo
          </label>
        </div>

        <div className="mt-4">
          <Button
            disabled={createStatus === 'loading'}
            size="md"
            type="submit"
          >
            {createStatus === 'loading' ? 'Guardando...' : 'Crear producto'}
          </Button>
        </div>
      </form>
    </section>
  )
}

export default ProductosCreatePage

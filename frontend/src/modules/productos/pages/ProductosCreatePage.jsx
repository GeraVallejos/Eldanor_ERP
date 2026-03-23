import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { useDispatch, useSelector } from 'react-redux'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { z } from 'zod'
import ApiContractError from '@/components/ui/ApiContractError'
import Button from '@/components/ui/Button'
import { normalizeApiError } from '@/api/errors'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { normalizeUpperInput } from '@/lib/textFormat'
import { cn } from '@/lib/utils'
import { invalidateProductosCatalogCache } from '@/modules/productos/services/productosCatalogCache'
import { productosApi } from '@/modules/productos/store/api'
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
const unidadMedidaOptions = [
  { value: 'UN', label: 'Unidad' },
  { value: 'KG', label: 'Kilogramo' },
  { value: 'GR', label: 'Gramo' },
  { value: 'LT', label: 'Litro' },
  { value: 'MT', label: 'Metro' },
  { value: 'M2', label: 'Metro cuadrado' },
  { value: 'M3', label: 'Metro cubico' },
  { value: 'CJ', label: 'Caja' },
]

function applyOperationalRules(values) {
  const nextValues = { ...values }

  if (nextValues.tipo === 'SERVICIO') {
    nextValues.maneja_inventario = false
    nextValues.stock_minimo = 0
    nextValues.usa_lotes = false
    nextValues.usa_series = false
    nextValues.usa_vencimiento = false
  }

  if (!nextValues.maneja_inventario) {
    nextValues.stock_minimo = 0
    nextValues.usa_lotes = false
    nextValues.usa_series = false
    nextValues.usa_vencimiento = false
  }

  if (nextValues.usa_series) {
    nextValues.usa_lotes = true
    nextValues.permite_decimales = false
  }

  return nextValues
}

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
    unidad_medida: z.string().min(1, 'Unidad requerida.'),
    permite_decimales: z.boolean(),
    maneja_inventario: z.boolean(),
    stock_minimo: z.number({ error: 'Stock minimo invalido.' }).min(0, 'No puede ser negativo.'),
    usa_lotes: z.boolean(),
    usa_series: z.boolean(),
    usa_vencimiento: z.boolean(),
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
    }

    if (values.usa_series && values.permite_decimales) {
      ctx.addIssue({
        code: 'custom',
        path: ['permite_decimales'],
        message: 'Un producto con series no debe permitir decimales.',
      })
    }
  })

function ProductosCreatePage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const categorias = useSelector(selectCategorias)
  const impuestos = useSelector(selectImpuestos)
  const catalogStatus = useSelector(selectCatalogStatus)
  const catalogError = useSelector(selectCatalogError)
  const createStatus = useSelector(selectCreateProductoStatus)
  const createError = useSelector(selectCreateProductoError)
  const [pageStatus, setPageStatus] = useState('idle')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)
  const isEditMode = Boolean(id)

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
      unidad_medida: 'UN',
      permite_decimales: true,
      maneja_inventario: true,
      stock_minimo: 0,
      usa_lotes: false,
      usa_series: false,
      usa_vencimiento: false,
      activo: true,
    },
  })

  const tipoSeleccionado = useWatch({ control, name: 'tipo' })
  const manejaInventarioSeleccionado = useWatch({ control, name: 'maneja_inventario' })
  const usaSeriesSeleccionado = useWatch({ control, name: 'usa_series' })
  const permiteDecimalesSeleccionado = useWatch({ control, name: 'permite_decimales' })

  useEffect(() => {
    if (catalogStatus === 'idle') {
      dispatch(fetchCatalogosProducto())
    }
  }, [catalogStatus, dispatch])

  useEffect(() => {
    let active = true

    const loadProducto = async () => {
      if (!isEditMode) {
        setPageStatus('idle')
        return
      }

      setPageStatus('loading')
      try {
        const data = await productosApi.getOne(productosApi.endpoints.productos, id)
        if (!active) {
          return
        }
        reset({
          nombre: data.nombre || '',
          descripcion: data.descripcion || '',
          sku: data.sku || '',
          tipo: data.tipo || 'PRODUCTO',
          categoria: data.categoria ? String(data.categoria) : '',
          impuesto: data.impuesto ? String(data.impuesto) : '',
          precio_referencia: Number(data.precio_referencia ?? 0),
          precio_costo: Number(data.precio_costo ?? 0),
          unidad_medida: data.unidad_medida || 'UN',
          permite_decimales: Boolean(data.permite_decimales ?? true),
          maneja_inventario: Boolean(data.maneja_inventario),
          stock_minimo: Number(data.stock_minimo ?? 0),
          usa_lotes: Boolean(data.usa_lotes),
          usa_series: Boolean(data.usa_series),
          usa_vencimiento: Boolean(data.usa_vencimiento),
          activo: Boolean(data.activo),
        })
        setPageStatus('succeeded')
      } catch (error) {
        if (!active) {
          return
        }
        setPageStatus('failed')
        toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar el producto.' }))
      }
    }

    void loadProducto()

    return () => {
      active = false
    }
  }, [id, isEditMode, reset])

  useEffect(() => {
    if (tipoSeleccionado === 'SERVICIO') {
      setValue('maneja_inventario', false, { shouldValidate: true })
      setValue('stock_minimo', 0, { shouldValidate: true })
      setValue('usa_lotes', false, { shouldValidate: true })
      setValue('usa_series', false, { shouldValidate: true })
      setValue('usa_vencimiento', false, { shouldValidate: true })
    }
  }, [setValue, tipoSeleccionado])

  useEffect(() => {
    if (!manejaInventarioSeleccionado) {
      setValue('stock_minimo', 0, { shouldValidate: true })
      setValue('usa_lotes', false, { shouldValidate: true })
      setValue('usa_series', false, { shouldValidate: true })
      setValue('usa_vencimiento', false, { shouldValidate: true })
    }
  }, [manejaInventarioSeleccionado, setValue])

  useEffect(() => {
    if (usaSeriesSeleccionado) {
      setValue('usa_lotes', true, { shouldValidate: true })
      setValue('permite_decimales', false, { shouldValidate: true })
    }
  }, [setValue, usaSeriesSeleccionado])

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
    setSubmitError(null)
    setSubmitting(true)

    const payload = applyOperationalRules({
      ...values,
      categoria: values.categoria || null,
      impuesto: values.impuesto || null,
      descripcion: values.descripcion?.trim() || '',
      maneja_inventario: values.tipo === 'SERVICIO' ? false : values.maneja_inventario,
    })

    if (isEditMode) {
      delete payload.precio_costo
    }

    try {
      if (isEditMode) {
        await productosApi.updateOne(productosApi.endpoints.productos, id, payload)
      } else {
        await dispatch(createProducto(payload)).unwrap()
      }
      invalidateProductosCatalogCache()
      toast.success(isEditMode ? 'Producto actualizado correctamente.' : 'Producto creado correctamente.')
      dispatch(fetchProductos())
      dispatch(resetCreateProductoState())
      if (isEditMode) {
        navigate(`/productos/${id}`)
        return
      }
      reset({
        nombre: '',
        descripcion: '',
        sku: '',
        tipo: 'PRODUCTO',
        categoria: '',
        impuesto: '',
        precio_referencia: 0,
        precio_costo: 0,
        unidad_medida: 'UN',
        permite_decimales: true,
        maneja_inventario: true,
        stock_minimo: 0,
        usa_lotes: false,
        usa_series: false,
        usa_vencimiento: false,
        activo: true,
      })
    } catch (error) {
      if (isEditMode) {
        const normalizedError = normalizeApiError(error, { fallback: 'No se pudo actualizar el producto.' })
        setSubmitError(error?.response?.data || null)
        toast.error(normalizedError)
        return
      }
      toast.error(typeof error === 'string' ? error : (error?.message || 'No se pudo crear el producto.'))
    } finally {
      setSubmitting(false)
    }
  }

  if (isEditMode && pageStatus === 'loading') {
    return <p className="text-sm text-muted-foreground">Cargando producto...</p>
  }

  if (isEditMode && pageStatus === 'failed') {
    return (
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-semibold">Editar producto</h2>
            <p className="text-sm text-muted-foreground">No fue posible cargar el producto solicitado.</p>
          </div>
          <Link
            to="/productos"
            className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}
          >
            Volver al listado
          </Link>
        </div>
      </section>
    )
  }

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">{isEditMode ? 'Editar producto' : 'Nuevo producto'}</h2>
          <p className="text-sm text-muted-foreground">
            {isEditMode ? 'Actualice los datos maestros del producto.' : 'Formulario seguro para alta de productos.'}
          </p>
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
          error={typeof (isEditMode ? submitError : createError) === 'object' ? (isEditMode ? submitError : createError) : null}
          title={isEditMode ? 'No se pudo actualizar el producto.' : 'No se pudo crear el producto.'}
        />
        <div className="grid gap-3 md:grid-cols-2">
          <label className="text-sm">
            Nombre
            <input
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              {...register('nombre', {
                onChange: (event) => {
                  event.target.value = normalizeUpperInput(event.target.value)
                },
              })}
            />
            {errors.nombre && <span className="mt-1 block text-xs text-destructive">{errors.nombre.message}</span>}
          </label>

          <label className="text-sm">
            SKU
            <input
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              {...register('sku', {
                onChange: (event) => {
                  event.target.value = normalizeUpperInput(event.target.value)
                },
              })}
            />
            {errors.sku && <span className="mt-1 block text-xs text-destructive">{errors.sku.message}</span>}
          </label>

          <label className="text-sm md:col-span-2">
            Descripcion
            <textarea
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              rows={3}
              {...register('descripcion', {
                onChange: (event) => {
                  event.target.value = normalizeUpperInput(event.target.value)
                },
              })}
            />
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
            <input type="number" step="0.01" min="0" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" {...register('precio_referencia', { valueAsNumber: true })} />
            {errors.precio_referencia && <span className="mt-1 block text-xs text-destructive">{errors.precio_referencia.message}</span>}
          </label>

          <label className="text-sm">
            Precio costo
            <input
              type="number"
              step="0.01"
              min="0"
              disabled={isEditMode}
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 disabled:cursor-not-allowed disabled:opacity-70"
              {...register('precio_costo', { valueAsNumber: true })}
            />
            {errors.precio_costo && <span className="mt-1 block text-xs text-destructive">{errors.precio_costo.message}</span>}
            {isEditMode ? (
              <span className="mt-1 block text-xs text-muted-foreground">
                El costo se actualiza desde documentos, recepciones o ajustes autorizados; no desde el maestro.
              </span>
            ) : null}
          </label>

          <label className="text-sm">
            Unidad
            <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" {...register('unidad_medida')}>
              {unidadMedidaOptions.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
            {errors.unidad_medida && <span className="mt-1 block text-xs text-destructive">{errors.unidad_medida.message}</span>}
          </label>

          <label className="text-sm">
            Stock minimo
            <input
              type="number"
              step={permiteDecimalesSeleccionado ? '0.01' : '1'}
              min="0"
              disabled={!manejaInventarioSeleccionado || tipoSeleccionado === 'SERVICIO'}
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              {...register('stock_minimo', { valueAsNumber: true })}
            />
            {errors.stock_minimo && <span className="mt-1 block text-xs text-destructive">{errors.stock_minimo.message}</span>}
          </label>

          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" {...register('permite_decimales')} disabled={usaSeriesSeleccionado} />
            Permite decimales
          </label>

          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" disabled={tipoSeleccionado === 'SERVICIO'} {...register('maneja_inventario')} />
            Maneja inventario
          </label>

          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" disabled={!manejaInventarioSeleccionado || tipoSeleccionado === 'SERVICIO'} {...register('usa_lotes')} />
            Usa lotes
          </label>

          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" disabled={!manejaInventarioSeleccionado || tipoSeleccionado === 'SERVICIO'} {...register('usa_series')} />
            Usa series
          </label>

          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" disabled={!manejaInventarioSeleccionado || tipoSeleccionado === 'SERVICIO'} {...register('usa_vencimiento')} />
            Usa vencimiento
          </label>

          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" {...register('activo')} />
            Activo
          </label>

          <p className="text-xs text-muted-foreground md:col-span-2">
            El stock actual se gestiona desde inventario. La ficha de producto solo mantiene datos maestros del catalogo.
          </p>
        </div>

        <div className="mt-4">
          <Button
            disabled={submitting || (createStatus === 'loading' && !isEditMode)}
            size="md"
            type="submit"
          >
            {submitting || (createStatus === 'loading' && !isEditMode)
              ? 'Guardando...'
              : (isEditMode ? 'Guardar cambios' : 'Crear producto')}
          </Button>
        </div>
      </form>
    </section>
  )
}

export default ProductosCreatePage

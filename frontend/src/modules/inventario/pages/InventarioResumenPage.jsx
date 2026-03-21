import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { formatCurrencyCLP, formatSmartNumber } from '@/lib/numberFormat'
import { cn } from '@/lib/utils'

function normalizeListResponse(data) {
  if (Array.isArray(data)) {
    return data
  }

  if (Array.isArray(data?.results)) {
    return data.results
  }

  return []
}

function formatNumber(value) {
  return formatSmartNumber(value, { maximumFractionDigits: 2 })
}

function InventarioResumenPage() {
  const [stocks, setStocks] = useState([])
  const [resumen, setResumen] = useState(null)
  const [criticos, setCriticos] = useState([])
  const [resumenMovimientos, setResumenMovimientos] = useState(null)

  const loadPanel = useCallback(async () => {
    try {
      const [{ data: stocksData }, { data: resumenData }, { data: criticosData }, { data: movimientosData }] =
        await Promise.all([
          api.get('/stocks/', { suppressGlobalErrorToast: true }),
          api.get('/stocks/resumen/', {
            params: { group_by: 'producto' },
            suppressGlobalErrorToast: true,
          }),
          api.get('/stocks/criticos/', { suppressGlobalErrorToast: true }),
          api.get('/movimientos-inventario/resumen_operativo/', { suppressGlobalErrorToast: true }),
        ])

      setStocks(normalizeListResponse(stocksData))
      setResumen(resumenData)
      setCriticos(Array.isArray(criticosData?.detalle) ? criticosData.detalle : [])
      setResumenMovimientos(movimientosData)
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar el panel de inventario.' }))
    }
  }, [])

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void loadPanel()
    }, 0)

    return () => clearTimeout(timeoutId)
  }, [loadPanel])

  const stockGeneral = useMemo(
    () => stocks.reduce((acc, row) => acc + Number(row.stock || 0), 0),
    [stocks],
  )

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold">Resumen de inventario</h2>
        <p className="text-sm text-muted-foreground">
          Panel ejecutivo con salud del stock, alertas y accesos rapidos a operacion y reportes.
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <article className="rounded-md border border-border bg-card p-4">
          <p className="text-sm text-muted-foreground">Stock total reportado</p>
          <p className="text-xl font-semibold">{formatNumber(resumen?.totales?.stock_total || 0)}</p>
        </article>
        <article className="rounded-md border border-border bg-card p-4">
          <p className="text-sm text-muted-foreground">Valor total inventario</p>
          <p className="text-xl font-semibold">{formatCurrencyCLP(resumen?.totales?.valor_total || 0)}</p>
        </article>
        <article className="rounded-md border border-border bg-card p-4">
          <p className="text-sm text-muted-foreground">Stock general cargado</p>
          <p className="text-xl font-semibold">{formatNumber(stockGeneral)}</p>
        </article>
      </div>

      {resumenMovimientos ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <article className="rounded-md border border-border bg-card p-4">
            <p className="text-sm text-muted-foreground">Movimientos registrados</p>
            <p className="text-xl font-semibold">{formatNumber(resumenMovimientos.total_movimientos || 0)}</p>
            <p className="mt-1 text-sm text-muted-foreground">Ajustes: {formatNumber(resumenMovimientos.ajustes || 0)}</p>
          </article>
          <article className="rounded-md border border-border bg-card p-4">
            <p className="text-sm text-muted-foreground">Entradas</p>
            <p className="text-xl font-semibold">{formatNumber(resumenMovimientos.cantidad_entrada || 0)}</p>
            <p className="mt-1 text-sm text-muted-foreground">Eventos: {formatNumber(resumenMovimientos.entradas || 0)}</p>
          </article>
          <article className="rounded-md border border-border bg-card p-4">
            <p className="text-sm text-muted-foreground">Salidas</p>
            <p className="text-xl font-semibold">{formatNumber(resumenMovimientos.cantidad_salida || 0)}</p>
            <p className="mt-1 text-sm text-muted-foreground">Eventos: {formatNumber(resumenMovimientos.salidas || 0)}</p>
          </article>
          <article className="rounded-md border border-border bg-card p-4">
            <p className="text-sm text-muted-foreground">Neto de unidades</p>
            <p className="text-xl font-semibold">{formatNumber(resumenMovimientos.neto_unidades || 0)}</p>
            <p className="mt-1 text-sm text-muted-foreground">Traslados: {formatNumber(resumenMovimientos.traslados || 0)}</p>
          </article>
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-sm text-muted-foreground">Lectura analitica</p>
          <h3 className="mt-1 text-lg font-semibold">Reportes de inventario</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Revisa stock valorizado, criticidad, agrupaciones y exportaciones por producto o bodega.
          </p>
          <Link to="/inventario/reportes" className={cn(buttonVariants({ variant: 'outline', size: 'md' }), 'mt-4')}>
            Ir a reportes
          </Link>
        </div>

        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-sm text-muted-foreground">Historial auditable</p>
          <h3 className="mt-1 text-lg font-semibold">Kardex</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Consulta entradas, salidas, ajustes y documentos con trazabilidad valorizada.
          </p>
          <Link to="/inventario/kardex" className={cn(buttonVariants({ variant: 'outline', size: 'md' }), 'mt-4')}>
            Ir a kardex
          </Link>
        </div>

        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-sm text-muted-foreground">Operaciones sensibles</p>
          <h3 className="mt-1 text-lg font-semibold">Ajustes de inventario</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Gestiona conteos fisicos, previsualiza diferencias y aplica regularizaciones con trazabilidad.
          </p>
          <Link to="/inventario/ajustes" className={cn(buttonVariants({ variant: 'outline', size: 'md' }), 'mt-4')}>
            Ir a ajustes
          </Link>
        </div>

        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-sm text-muted-foreground">Movimientos internos</p>
          <h3 className="mt-1 text-lg font-semibold">Traslados entre bodegas</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Registra traspasos internos y consulta sus ultimos movimientos desde una vista dedicada.
          </p>
          <Link to="/inventario/traslados" className={cn(buttonVariants({ variant: 'outline', size: 'md' }), 'mt-4')}>
            Ir a traslados
          </Link>
        </div>
      </div>

      <div className="rounded-md border border-border bg-card p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold">Stock critico</h3>
            <p className="text-sm text-muted-foreground">Productos bajo o al limite de stock minimo.</p>
          </div>
          <span className="rounded-full bg-muted px-3 py-1 text-sm font-medium">{criticos.length}</span>
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="px-3 py-2 text-left font-medium">Producto</th>
                <th className="px-3 py-2 text-left font-medium">SKU</th>
                <th className="px-3 py-2 text-left font-medium">Stock</th>
                <th className="px-3 py-2 text-left font-medium">Minimo</th>
                <th className="px-3 py-2 text-left font-medium">Faltante</th>
              </tr>
            </thead>
            <tbody>
              {criticos.length > 0 ? (
                criticos.map((row) => (
                  <tr key={row.producto_id} className="border-t border-border">
                    <td className="px-3 py-2">{row.producto__nombre}</td>
                    <td className="px-3 py-2">{row.producto__sku || '-'}</td>
                    <td className="px-3 py-2">{formatNumber(row.stock_total)}</td>
                    <td className="px-3 py-2">{formatNumber(row.producto__stock_minimo)}</td>
                    <td className="px-3 py-2 font-medium text-destructive">{formatNumber(row.faltante)}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="px-3 py-3 text-muted-foreground" colSpan={5}>No hay productos en nivel critico.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}

export default InventarioResumenPage

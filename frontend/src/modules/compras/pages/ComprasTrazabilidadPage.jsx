import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { formatDateChile } from '@/lib/dateTimeFormat'
import { formatCurrencyCLP } from '@/lib/numberFormat'
import { cn } from '@/lib/utils'

const TIPO_LABELS = {
  GUIA_RECEPCION: 'Guia de recepcion',
  FACTURA_COMPRA: 'Factura de compra',
  BOLETA_COMPRA: 'Boleta de compra',
}

function ComprasTrazabilidadPage() {
  const { id } = useParams()
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const response = await api.get(`/ordenes-compra/${id}/trazabilidad/`, {
        suppressGlobalErrorToast: true,
      })
      setData(response.data)
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar la trazabilidad de la orden.' }))
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void loadData()
    }, 0)
    return () => clearTimeout(timeoutId)
  }, [loadData])

  const timeline = useMemo(() => {
    const recepciones = Array.isArray(data?.recepciones)
      ? data.recepciones.map((row) => ({
          ...row,
          tipo: 'RECEPCION',
          fecha_referencia: row.fecha,
          to: `/compras/recepciones/${row.id}/editar`,
          titulo: `Recepcion ${formatDateChile(row.fecha)}`,
        }))
      : []

    const documentos = Array.isArray(data?.documentos)
      ? data.documentos.map((row) => ({
          ...row,
          tipo: 'DOCUMENTO',
          fecha_referencia: row.fecha_emision,
          to: `/compras/documentos/${row.id}`,
          titulo: `${TIPO_LABELS[row.tipo_documento] || row.tipo_documento} ${row.serie ? `${row.serie}-` : ''}${row.folio || 'S/F'}`,
        }))
      : []

    return [...recepciones, ...documentos].sort((a, b) =>
      String(b.fecha_referencia || '').localeCompare(String(a.fecha_referencia || '')),
    )
  }, [data])

  if (loading) {
    return <p className="text-sm text-muted-foreground">Cargando trazabilidad de abastecimiento...</p>
  }

  if (!data) {
    return (
      <section className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-2xl font-semibold">Trazabilidad de compras</h2>
          <Link to="/compras/ordenes" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
            Volver
          </Link>
        </div>
        <p className="rounded-md border border-border bg-card px-4 py-3 text-sm text-muted-foreground">
          No fue posible cargar la informacion de la orden.
        </p>
      </section>
    )
  }

  const orden = data.orden_compra
  const resumen = data.resumen

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Trazabilidad de compras</h2>
          <p className="text-sm text-muted-foreground">
            Seguimiento de la orden de compra, sus recepciones y los documentos tributarios asociados.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/compras/ordenes" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
            Volver
          </Link>
          <Link to={`/compras/ordenes/${id}`} className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
            Ver orden
          </Link>
        </div>
      </div>

      <div className="grid gap-3 xl:grid-cols-4">
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Orden</p>
          <p className="mt-2 text-2xl font-semibold">#{orden?.numero || '-'}</p>
          <p className="mt-1 text-sm text-muted-foreground">Estado: {orden?.estado || '-'}</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Recepciones</p>
          <p className="mt-2 text-2xl font-semibold">{resumen?.recepciones_total || 0}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Confirmadas: {resumen?.recepciones_confirmadas || 0}
          </p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Documentos</p>
          <p className="mt-2 text-2xl font-semibold">{resumen?.documentos_total || 0}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Confirmados: {resumen?.documentos_confirmados || 0}
          </p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Valor OC</p>
          <p className="mt-2 text-2xl font-semibold">{formatCurrencyCLP(orden?.total || 0)}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Docs ligados a recepcion: {resumen?.documentos_con_recepcion || 0}
          </p>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(340px,0.9fr)]">
        <div className="rounded-xl border border-border bg-card p-4">
          <div className="mb-3">
            <h3 className="text-lg font-semibold">Hilo de abastecimiento</h3>
            <p className="text-sm text-muted-foreground">
              Ordena cronologicamente recepciones y documentos nacidos desde esta orden de compra.
            </p>
          </div>
          <div className="space-y-3">
            {timeline.length === 0 ? (
              <p className="text-sm text-muted-foreground">Aun no existen recepciones ni documentos asociados.</p>
            ) : (
              timeline.map((row) => (
                <div key={`${row.tipo}-${row.id}`} className="rounded-lg border border-border px-3 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium">{row.titulo}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatDateChile(row.fecha_referencia)} - {row.estado || '-'}
                      </p>
                    </div>
                    {'total' in row ? (
                      <p className="text-sm font-medium">{formatCurrencyCLP(row.total || 0)}</p>
                    ) : null}
                  </div>
                  <div className="mt-2">
                    <Link to={row.to} className="text-sm text-primary hover:underline">
                      Ver detalle
                    </Link>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="mb-3">
              <h3 className="text-lg font-semibold">Recepciones asociadas</h3>
            </div>
            <div className="space-y-2">
              {(data.recepciones || []).length === 0 ? (
                <p className="text-sm text-muted-foreground">No hay recepciones registradas.</p>
              ) : (
                data.recepciones.map((row) => (
                  <Link key={row.id} to={`/compras/recepciones/${row.id}/editar`} className="block rounded-lg border border-border px-3 py-3 text-sm hover:bg-muted/30">
                    <p className="font-medium">Recepcion {formatDateChile(row.fecha)}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{row.estado || '-'}</p>
                  </Link>
                ))
              )}
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card p-4">
            <div className="mb-3">
              <h3 className="text-lg font-semibold">Documentos asociados</h3>
            </div>
            <div className="space-y-2">
              {(data.documentos || []).length === 0 ? (
                <p className="text-sm text-muted-foreground">No hay documentos de compra asociados.</p>
              ) : (
                data.documentos.map((row) => (
                  <Link key={row.id} to={`/compras/documentos/${row.id}`} className="block rounded-lg border border-border px-3 py-3 text-sm hover:bg-muted/30">
                    <p className="font-medium">
                      {TIPO_LABELS[row.tipo_documento] || row.tipo_documento} {row.serie ? `${row.serie}-` : ''}{row.folio || 'S/F'}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {formatDateChile(row.fecha_emision)} - {row.estado || '-'}
                    </p>
                  </Link>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default ComprasTrazabilidadPage

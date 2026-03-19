import { useCallback, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import BulkImportButton from '@/components/ui/BulkImportButton'
import { usePermission } from '@/modules/shared/auth/usePermission'

function normalizeListResponse(data) {
  if (Array.isArray(data)) {
    return data
  }
  if (Array.isArray(data?.results)) {
    return data.results
  }
  return []
}

function formatTipoDocumento(value) {
  const mapping = {
    FACTURA_VENTA: 'Factura venta',
    GUIA_DESPACHO: 'Guia despacho',
    NOTA_CREDITO_VENTA: 'Nota credito',
  }
  return mapping[value] || value
}

function AdministracionSiiPage() {
  const canView = usePermission('FACTURACION.VER')
  const canEdit = usePermission('FACTURACION.EDITAR')
  const [loading, setLoading] = useState(true)
  const [savingConfig, setSavingConfig] = useState(false)
  const [savingRange, setSavingRange] = useState(false)
  const [configuracion, setConfiguracion] = useState(null)
  const [rangos, setRangos] = useState([])
  const [configForm, setConfigForm] = useState({
    ambiente: 'CERTIFICACION',
    rut_emisor: '',
    razon_social: '',
    certificado_alias: '',
    certificado_activo: false,
    resolucion_numero: '',
    resolucion_fecha: '',
    email_intercambio_dte: '',
    proveedor_envio: 'INTERNO',
    activa: true,
  })
  const [rangeForm, setRangeForm] = useState({
    tipo_documento: 'FACTURA_VENTA',
    caf_nombre: '',
    folio_desde: '',
    folio_hasta: '',
    folio_actual: '',
    fecha_autorizacion: '',
    fecha_vencimiento: '',
    activo: true,
  })

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [{ data: configData }, { data: rangosData }] = await Promise.all([
        api.get('/configuracion-tributaria/', { suppressGlobalErrorToast: true }),
        api.get('/rangos-folios-tributarios/', { suppressGlobalErrorToast: true }),
      ])

      const configList = normalizeListResponse(configData)
      const ranges = normalizeListResponse(rangosData).sort((left, right) => String(left.tipo_documento).localeCompare(String(right.tipo_documento)))

      setConfiguracion(configList[0] || null)
      setRangos(ranges)

      if (configList[0]) {
        const current = configList[0]
        setConfigForm({
          ambiente: current.ambiente || 'CERTIFICACION',
          rut_emisor: current.rut_emisor || '',
          razon_social: current.razon_social || '',
          certificado_alias: current.certificado_alias || '',
          certificado_activo: Boolean(current.certificado_activo),
          resolucion_numero: current.resolucion_numero || '',
          resolucion_fecha: current.resolucion_fecha || '',
          email_intercambio_dte: current.email_intercambio_dte || '',
          proveedor_envio: current.proveedor_envio || 'INTERNO',
          activa: Boolean(current.activa),
        })
      }
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar la configuracion SII.' }))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!canView) {
      return
    }
    void loadData()
  }, [canView, loadData])

  const rangoStats = useMemo(() => {
    const activos = rangos.filter((item) => item.activo)
    const proximos = activos.filter((item) => {
      const actual = Number(item.folio_actual || item.folio_desde || 0)
      const hasta = Number(item.folio_hasta || 0)
      return hasta > 0 && hasta - actual <= 20
    })
    return { activos: activos.length, proximos: proximos.length }
  }, [rangos])

  const handleConfigSubmit = async (event) => {
    event.preventDefault()
    setSavingConfig(true)
    try {
      if (configuracion?.id) {
        await api.patch(`/configuracion-tributaria/${configuracion.id}/`, configForm, { suppressGlobalErrorToast: true })
        toast.success('Configuracion tributaria actualizada.')
      } else {
        await api.post('/configuracion-tributaria/', configForm, { suppressGlobalErrorToast: true })
        toast.success('Configuracion tributaria creada.')
      }
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo guardar la configuracion tributaria.' }))
    } finally {
      setSavingConfig(false)
    }
  }

  const handleRangeSubmit = async (event) => {
    event.preventDefault()
    setSavingRange(true)
    try {
      await api.post('/rangos-folios-tributarios/', rangeForm, { suppressGlobalErrorToast: true })
      toast.success('Rango tributario registrado.')
      setRangeForm({
        tipo_documento: 'FACTURA_VENTA',
        caf_nombre: '',
        folio_desde: '',
        folio_hasta: '',
        folio_actual: '',
        fecha_autorizacion: '',
        fecha_vencimiento: '',
        activo: true,
      })
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo registrar el rango tributario.' }))
    } finally {
      setSavingRange(false)
    }
  }

  if (!canView) {
    return <p className="text-sm text-destructive">No tiene permiso para revisar configuracion SII.</p>
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">SII y DTE</h2>
          <p className="text-sm text-muted-foreground">Configuracion administrativa de emision tributaria, certificados y control de folios.</p>
        </div>
        {canEdit ? (
          <BulkImportButton endpoint="/rangos-folios-tributarios/bulk_import/" templateEndpoint="/rangos-folios-tributarios/bulk_template/" onCompleted={() => { void loadData() }} />
        ) : null}
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Ambiente</p>
          <p className="mt-2 text-2xl font-semibold">{configuracion?.ambiente || 'Sin definir'}</p>
          <p className="mt-1 text-xs text-muted-foreground">Certificacion para pruebas o produccion real.</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Certificado</p>
          <p className="mt-2 text-2xl font-semibold">{configuracion?.certificado_activo ? 'Operativo' : 'Pendiente'}</p>
          <p className="mt-1 text-xs text-muted-foreground">Debe estar activo antes de una salida comercial amplia.</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Rangos activos</p>
          <p className="mt-2 text-2xl font-semibold">{rangoStats.activos}</p>
          <p className="mt-1 text-xs text-muted-foreground">Cobertura disponible por tipo de documento.</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Proximos a agotarse</p>
          <p className="mt-2 text-2xl font-semibold">{rangoStats.proximos}</p>
          <p className="mt-1 text-xs text-muted-foreground">Conviene renovar CAF antes de llegar al limite.</p>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <form className="grid gap-3 rounded-xl border border-border bg-card p-4 md:grid-cols-2" onSubmit={handleConfigSubmit}>
          <div className="md:col-span-2">
            <h3 className="text-lg font-semibold">Configuracion tributaria</h3>
            <p className="text-sm text-muted-foreground">Mantenga aqui solo lo esencial para operar y auditar.</p>
          </div>
          <label className="text-sm">
            Ambiente
            <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={configForm.ambiente} onChange={(event) => setConfigForm((prev) => ({ ...prev, ambiente: event.target.value }))} disabled={!canEdit}>
              <option value="CERTIFICACION">Certificacion</option>
              <option value="PRODUCCION">Produccion</option>
            </select>
          </label>
          <label className="text-sm">
            RUT emisor
            <input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={configForm.rut_emisor} onChange={(event) => setConfigForm((prev) => ({ ...prev, rut_emisor: event.target.value }))} disabled={!canEdit} required />
          </label>
          <label className="text-sm md:col-span-2">
            Razon social
            <input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={configForm.razon_social} onChange={(event) => setConfigForm((prev) => ({ ...prev, razon_social: event.target.value }))} disabled={!canEdit} required />
          </label>
          <label className="text-sm">
            Alias certificado
            <input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={configForm.certificado_alias} onChange={(event) => setConfigForm((prev) => ({ ...prev, certificado_alias: event.target.value }))} disabled={!canEdit} />
          </label>
          <label className="text-sm">
            Proveedor envio
            <input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={configForm.proveedor_envio} onChange={(event) => setConfigForm((prev) => ({ ...prev, proveedor_envio: event.target.value }))} disabled={!canEdit} />
          </label>
          <label className="text-sm">
            Resolucion numero
            <input type="number" min="0" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={configForm.resolucion_numero} onChange={(event) => setConfigForm((prev) => ({ ...prev, resolucion_numero: event.target.value }))} disabled={!canEdit} />
          </label>
          <label className="text-sm">
            Resolucion fecha
            <input type="date" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={configForm.resolucion_fecha} onChange={(event) => setConfigForm((prev) => ({ ...prev, resolucion_fecha: event.target.value }))} disabled={!canEdit} />
          </label>
          <label className="text-sm md:col-span-2">
            Email intercambio DTE
            <input type="email" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={configForm.email_intercambio_dte} onChange={(event) => setConfigForm((prev) => ({ ...prev, email_intercambio_dte: event.target.value }))} disabled={!canEdit} />
          </label>
          <div className="flex flex-wrap items-center gap-4 md:col-span-2">
            <label className="inline-flex items-center gap-2 text-sm">
              <input type="checkbox" checked={configForm.certificado_activo} onChange={(event) => setConfigForm((prev) => ({ ...prev, certificado_activo: event.target.checked }))} disabled={!canEdit} />
              Certificado operativo
            </label>
            <label className="inline-flex items-center gap-2 text-sm">
              <input type="checkbox" checked={configForm.activa} onChange={(event) => setConfigForm((prev) => ({ ...prev, activa: event.target.checked }))} disabled={!canEdit} />
              Configuracion activa
            </label>
            {canEdit ? (
              <Button type="submit" disabled={savingConfig}>{savingConfig ? 'Guardando...' : configuracion?.id ? 'Actualizar configuracion' : 'Crear configuracion'}</Button>
            ) : null}
          </div>
        </form>

        <form className="grid gap-3 rounded-xl border border-border bg-card p-4 md:grid-cols-2" onSubmit={handleRangeSubmit}>
          <div className="md:col-span-2">
            <h3 className="text-lg font-semibold">Alta rapida de folios</h3>
            <p className="text-sm text-muted-foreground">Para ajustes rapidos; la carga XLSX sirve para varios rangos.</p>
          </div>
          <label className="text-sm">
            Tipo documento
            <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={rangeForm.tipo_documento} onChange={(event) => setRangeForm((prev) => ({ ...prev, tipo_documento: event.target.value }))} disabled={!canEdit}>
              <option value="FACTURA_VENTA">Factura venta</option>
              <option value="GUIA_DESPACHO">Guia despacho</option>
              <option value="NOTA_CREDITO_VENTA">Nota credito venta</option>
            </select>
          </label>
          <label className="text-sm">
            Nombre CAF
            <input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={rangeForm.caf_nombre} onChange={(event) => setRangeForm((prev) => ({ ...prev, caf_nombre: event.target.value }))} disabled={!canEdit} required />
          </label>
          <label className="text-sm">
            Folio desde
            <input type="number" min="1" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={rangeForm.folio_desde} onChange={(event) => setRangeForm((prev) => ({ ...prev, folio_desde: event.target.value }))} disabled={!canEdit} required />
          </label>
          <label className="text-sm">
            Folio hasta
            <input type="number" min="1" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={rangeForm.folio_hasta} onChange={(event) => setRangeForm((prev) => ({ ...prev, folio_hasta: event.target.value }))} disabled={!canEdit} required />
          </label>
          <label className="text-sm">
            Folio actual
            <input type="number" min="1" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={rangeForm.folio_actual} onChange={(event) => setRangeForm((prev) => ({ ...prev, folio_actual: event.target.value }))} disabled={!canEdit} />
          </label>
          <label className="text-sm">
            Fecha autorizacion
            <input type="date" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={rangeForm.fecha_autorizacion} onChange={(event) => setRangeForm((prev) => ({ ...prev, fecha_autorizacion: event.target.value }))} disabled={!canEdit} />
          </label>
          <label className="text-sm">
            Fecha vencimiento
            <input type="date" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={rangeForm.fecha_vencimiento} onChange={(event) => setRangeForm((prev) => ({ ...prev, fecha_vencimiento: event.target.value }))} disabled={!canEdit} />
          </label>
          <div className="flex items-center gap-4 md:col-span-2">
            <label className="inline-flex items-center gap-2 text-sm">
              <input type="checkbox" checked={rangeForm.activo} onChange={(event) => setRangeForm((prev) => ({ ...prev, activo: event.target.checked }))} disabled={!canEdit} />
              Rango activo
            </label>
            {canEdit ? (
              <Button type="submit" disabled={savingRange}>{savingRange ? 'Guardando...' : 'Agregar rango'}</Button>
            ) : null}
          </div>
        </form>
      </div>

      <div className="rounded-xl border border-border bg-card p-4">
        <div className="mb-3">
          <h3 className="text-lg font-semibold">Rangos tributarios</h3>
          <p className="text-sm text-muted-foreground">Vista de control para disponibilidad, vigencia y consumo.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="px-3 py-2 text-left font-medium">Documento</th>
                <th className="px-3 py-2 text-left font-medium">CAF</th>
                <th className="px-3 py-2 text-left font-medium">Rango</th>
                <th className="px-3 py-2 text-left font-medium">Actual</th>
                <th className="px-3 py-2 text-left font-medium">Vencimiento</th>
                <th className="px-3 py-2 text-left font-medium">Estado</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td className="px-3 py-3 text-muted-foreground" colSpan={6}>Cargando rangos...</td></tr>
              ) : rangos.length === 0 ? (
                <tr><td className="px-3 py-3 text-muted-foreground" colSpan={6}>No hay rangos de folios cargados.</td></tr>
              ) : (
                rangos.map((item) => (
                  <tr key={item.id} className="border-t border-border">
                    <td className="px-3 py-2">{formatTipoDocumento(item.tipo_documento)}</td>
                    <td className="px-3 py-2">{item.caf_nombre}</td>
                    <td className="px-3 py-2">{item.folio_desde} - {item.folio_hasta}</td>
                    <td className="px-3 py-2">{item.folio_actual || item.folio_desde}</td>
                    <td className="px-3 py-2">{item.fecha_vencimiento || '-'}</td>
                    <td className="px-3 py-2">{item.activo ? 'Activo' : 'Inactivo'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}

export default AdministracionSiiPage

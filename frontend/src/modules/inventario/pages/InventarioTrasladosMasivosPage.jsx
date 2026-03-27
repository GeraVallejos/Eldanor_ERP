import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import { normalizeApiError } from '@/api/errors'
import BulkImportButton from '@/components/ui/BulkImportButton'
import Button from '@/components/ui/Button'
import SearchableSelect from '@/components/ui/SearchableSelect'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { cn } from '@/lib/utils'
import { inventarioApi } from '@/modules/inventario/store'
import { mergeProductosCatalog, searchProductosCatalog } from '@/modules/productos/services/productosCatalogCache'

function normalizeListResponse(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

function buildRow() {
  return {
    id: `${Date.now()}-${Math.random()}`,
    producto_id: '',
    cantidad: '',
  }
}

function buildRows(count = 1) {
  return Array.from({ length: count }, () => buildRow())
}

function buildReference({ motivo, referenciaOperativa, observaciones }) {
  return [motivo, referenciaOperativa, observaciones].map((value) => String(value || '').trim()).filter(Boolean).join(' | ')
}

function extractOperationalReference({ referencia, motivo, observaciones }) {
  const parts = String(referencia || '').split(' | ').map((value) => value.trim()).filter(Boolean)
  if (parts.length === 0) {
    return ''
  }
  if (parts.length === 1) {
    return parts[0] === String(motivo || '').trim() ? '' : parts[0]
  }
  const first = String(motivo || '').trim()
  const last = String(observaciones || '').trim()
  let middle = parts
  if (first && middle[0] === first) {
    middle = middle.slice(1)
  }
  if (last && middle[middle.length - 1] === last) {
    middle = middle.slice(0, -1)
  }
  return middle.join(' | ')
}

function InventarioTrasladosMasivosPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const draftId = searchParams.get('draft')
  const [productos, setProductos] = useState([])
  const [bodegas, setBodegas] = useState([])
  const [loadingProductos, setLoadingProductos] = useState(false)
  const [loadingDraft, setLoadingDraft] = useState(false)
  const [savingMode, setSavingMode] = useState(null)
  const [loadingList, setLoadingList] = useState(false)
  const [duplicatingId, setDuplicatingId] = useState(null)
  const [lastDocument, setLastDocument] = useState(null)
  const [recentDocuments, setRecentDocuments] = useState([])
  const [filters, setFilters] = useState({ q: '', estado: '', desde: '', hasta: '' })
  const [header, setHeader] = useState({
    motivo: '',
    referencia_operativa: '',
    observaciones: '',
    bodega_origen_id: '',
    bodega_destino_id: '',
  })
  const initialProductoId = searchParams.get('producto_id') || ''
  const initialCantidad = searchParams.get('cantidad') || ''
  const initialOrigenId = searchParams.get('bodega_origen_id') || ''
  const initialDestinoId = searchParams.get('bodega_destino_id') || ''
  const [rows, setRows] = useState([
    {
      ...buildRow(),
      producto_id: initialProductoId,
      cantidad: initialCantidad,
    },
  ])
  const bulkImportEndpoint = `${inventarioApi.endpoints.trasladosMasivos}bulk_import/`
  const bulkTemplateEndpoint = `${inventarioApi.endpoints.trasladosMasivos}bulk_template/`

  const loadRecentDocuments = useCallback(async (nextFilters) => {
    setLoadingList(true)
    try {
      const documentosData = await inventarioApi.getPaginated(inventarioApi.endpoints.trasladosMasivos, {
        page_size: 5,
        ...(nextFilters.estado ? { estado: nextFilters.estado } : {}),
        ...(nextFilters.desde ? { desde: nextFilters.desde } : {}),
        ...(nextFilters.hasta ? { hasta: nextFilters.hasta } : {}),
        ...(nextFilters.q ? { q: nextFilters.q } : {}),
      })
      setRecentDocuments(documentosData.results || [])
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los traslados masivos.' }))
    } finally {
      setLoadingList(false)
    }
  }, [])

  useEffect(() => {
    const loadData = async () => {
      try {
        const [productosData, bodegasData] = await Promise.all([
          searchProductosCatalog({ tipo: 'PRODUCTO' }),
          inventarioApi.getList(inventarioApi.endpoints.bodegas),
        ])
        setProductos(productosData)
        setBodegas(normalizeListResponse(bodegasData))
        await loadRecentDocuments({ q: '', estado: '', desde: '', hasta: '' })
      } catch (error) {
        toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los datos del traslado masivo.' }))
      }
    }
    void loadData()
  }, [loadRecentDocuments])

  useEffect(() => {
    if (!draftId) {
      return
    }

    const loadDraft = async () => {
      setLoadingDraft(true)
      try {
        const data = await inventarioApi.getOne(inventarioApi.endpoints.trasladosMasivos, draftId)
        if (data.estado !== 'BORRADOR') {
          toast.error('Solo se pueden editar traslados masivos en borrador.')
          navigate(`/inventario/traslados-masivos/${draftId}`, { replace: true })
          return
        }
        setHeader({
          motivo: data.motivo || '',
          referencia_operativa: extractOperationalReference({
            referencia: data.referencia,
            motivo: data.motivo,
            observaciones: data.observaciones,
          }),
          observaciones: data.observaciones || '',
          bodega_origen_id: data.bodega_origen ? String(data.bodega_origen) : '',
          bodega_destino_id: data.bodega_destino ? String(data.bodega_destino) : '',
        })
        setRows(
          (data.items || []).map((item, index) => ({
            id: `${item.id || index}`,
            producto_id: String(item.producto || ''),
            cantidad: String(item.cantidad ?? ''),
          })),
        )
        setLastDocument(data)
      } catch (error) {
        toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar el borrador del traslado masivo.' }))
      } finally {
        setLoadingDraft(false)
      }
    }

    void loadDraft()
  }, [draftId, navigate])

  useEffect(() => {
    if (draftId) {
      return
    }
    if (initialOrigenId || initialDestinoId) {
      setHeader((prev) => ({
        ...prev,
        bodega_origen_id: initialOrigenId || prev.bodega_origen_id,
        bodega_destino_id: initialDestinoId || prev.bodega_destino_id,
      }))
    }
  }, [draftId, initialDestinoId, initialOrigenId])

  const productoOptions = productos.map((producto) => ({
    value: String(producto.id),
    label: producto.nombre || `Producto ${producto.id}`,
    keywords: `${producto.sku || ''} ${producto.tipo || ''}`,
  }))
  const bodegaOptions = bodegas.map((bodega) => ({
    value: String(bodega.id),
    label: bodega.nombre || `Bodega ${bodega.id}`,
  }))

  const searchProductos = async (query) => {
    setLoadingProductos(true)
    try {
      const results = await searchProductosCatalog({ query, tipo: 'PRODUCTO' })
      setProductos((prev) => mergeProductosCatalog(prev, results))
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron buscar productos.' }))
    } finally {
      setLoadingProductos(false)
    }
  }

  const updateRow = (id, key, value) => {
    setRows((prev) => prev.map((row) => (row.id === id ? { ...row, [key]: value } : row)))
  }

  const rowDiagnostics = useMemo(() => {
    const duplicates = new Map()
    rows.forEach((row) => {
      if (!row.producto_id) {
        return
      }
      duplicates.set(row.producto_id, (duplicates.get(row.producto_id) || 0) + 1)
    })

    return rows.map((row) => {
      const errors = []
      if (!row.producto_id) {
        errors.push('Debe seleccionar un producto.')
      }
      if (row.cantidad === '') {
        errors.push('Debe informar cantidad.')
      } else if (Number(row.cantidad) <= 0) {
        errors.push('La cantidad debe ser mayor a cero.')
      }
      if (row.producto_id && (duplicates.get(row.producto_id) || 0) > 1) {
        errors.push('El producto no puede repetirse en el mismo traslado.')
      }
      return {
        id: row.id,
        errors,
        valid: errors.length === 0,
      }
    })
  }, [rows])
  const diagnosticsById = useMemo(
    () => new Map(rowDiagnostics.map((diagnostic) => [diagnostic.id, diagnostic])),
    [rowDiagnostics],
  )
  const headerErrors = useMemo(() => {
    const errors = []
    if (
      header.bodega_origen_id &&
      header.bodega_destino_id &&
      header.bodega_origen_id === header.bodega_destino_id
    ) {
      errors.push('La bodega destino debe ser distinta a la bodega origen.')
    }
    return errors
  }, [header.bodega_destino_id, header.bodega_origen_id])

  const invalidRowsCount = rowDiagnostics.filter((row) => !row.valid).length
  const validRowsCount = rowDiagnostics.length - invalidRowsCount

  const addRows = (count = 1) => setRows((prev) => [...prev, ...buildRows(count)])
  const removeRow = (id) => setRows((prev) => (prev.length === 1 ? prev : prev.filter((row) => row.id !== id)))
  const duplicateRow = (id) => {
    setRows((prev) => {
      const row = prev.find((item) => item.id === id)
      if (!row) {
        return prev
      }
      const clone = { ...row, id: `${Date.now()}-${Math.random()}` }
      const index = prev.findIndex((item) => item.id === id)
      return [...prev.slice(0, index + 1), clone, ...prev.slice(index + 1)]
    })
  }

  const handleSubmit = async (mode = 'CONFIRMADO') => {
    const referencia = buildReference(header)
    const items = rows
      .filter((row) => row.producto_id && row.cantidad)
      .map((row) => ({ producto_id: row.producto_id, cantidad: row.cantidad }))

    if (!header.motivo.trim()) {
      toast.error('Debe informar el motivo operativo del traslado masivo.')
      return
    }
    if (!header.bodega_origen_id || !header.bodega_destino_id) {
      toast.error('Debe informar bodega origen y destino.')
      return
    }
    if (headerErrors.length > 0) {
      toast.error(headerErrors[0])
      return
    }
    if (items.length === 0) {
      toast.error('Debe informar al menos una linea valida.')
      return
    }
    if (invalidRowsCount > 0) {
      toast.error('Corrige las lineas con error antes de guardar o confirmar el borrador.')
      return
    }

    setSavingMode(mode)
    try {
      const payload = {
        referencia,
        motivo: header.motivo,
        observaciones: header.observaciones,
        bodega_origen_id: header.bodega_origen_id,
        bodega_destino_id: header.bodega_destino_id,
        items,
      }
      let data = null
      if (draftId) {
        const draft = await inventarioApi.patchOne(inventarioApi.endpoints.trasladosMasivos, draftId, payload)
        data = mode === 'CONFIRMADO'
          ? await inventarioApi.executeDetailAction(inventarioApi.endpoints.trasladosMasivos, draft.id, 'confirmar')
          : draft
      } else {
        data = await inventarioApi.postOne(inventarioApi.endpoints.trasladosMasivos, {
          ...payload,
          estado: mode,
        })
      }
      setLastDocument(data)
      await loadRecentDocuments(filters)
      if (mode === 'BORRADOR') {
        toast.success(draftId ? 'Borrador de traslado masivo actualizado correctamente.' : 'Borrador de traslado masivo guardado correctamente.')
        if (!draftId) {
          navigate(`/inventario/traslados-masivos?draft=${data.id}`, { replace: true })
        }
      } else {
        toast.success('Traslado masivo confirmado correctamente.')
        navigate(`/inventario/traslados-masivos/${data.id}`, { replace: true })
      }
      if (!draftId && mode === 'BORRADOR') {
        setHeader({
          motivo: '',
          referencia_operativa: '',
          observaciones: '',
          bodega_origen_id: '',
          bodega_destino_id: '',
        })
        setRows([buildRow()])
      }
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: mode === 'BORRADOR' ? 'No se pudo guardar el borrador del traslado masivo.' : 'No se pudo confirmar el traslado masivo.' }))
    } finally {
      setSavingMode(null)
    }
  }

  const handleDuplicate = async (documentoId) => {
    setDuplicatingId(documentoId)
    try {
      const data = await inventarioApi.executeDetailAction(inventarioApi.endpoints.trasladosMasivos, documentoId, 'duplicar')
      setLastDocument(data)
      await loadRecentDocuments(filters)
      toast.success('Borrador de traslado masivo duplicado correctamente.')
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo duplicar el traslado masivo.' }))
    } finally {
      setDuplicatingId(null)
    }
  }

  const handleBulkImportCompleted = async (data) => {
    if (data?.documento) {
      setLastDocument(data.documento)
    }
    await loadRecentDocuments(filters)
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">{draftId ? 'Editar borrador de traslado masivo' : 'Traslado masivo entre bodegas'}</h2>
          <p className="text-sm text-muted-foreground">
            {draftId ? 'Actualiza el borrador antes de confirmar el movimiento definitivo entre bodegas.' : 'Confirma un documento con multiples traslados entre la misma bodega origen y destino.'}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <BulkImportButton
            endpoint={bulkImportEndpoint}
            templateEndpoint={bulkTemplateEndpoint}
            previewBeforeImport
            previewTitle="Confirmar importacion de traslados masivos"
            onCompleted={(data) => { void handleBulkImportCompleted(data) }}
          />
          <Link to={draftId ? `/inventario/traslados-masivos/${draftId}` : '/inventario/traslados'} className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
            {draftId ? 'Volver al detalle' : 'Volver a traslados simples'}
          </Link>
        </div>
      </div>

      <div className="rounded-md border border-border bg-card p-4">
        <p className="text-sm text-muted-foreground">
          La importacion por XLSX o CSV crea un borrador validado. El traslado no se ejecuta hasta confirmar el documento desde su detalle.
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Lineas</p>
          <p className="mt-1 text-lg font-semibold">{rows.length}</p>
        </div>
        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Validas</p>
          <p className="mt-1 text-lg font-semibold">{validRowsCount}</p>
        </div>
        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Con error</p>
          <p className="mt-1 text-lg font-semibold">{invalidRowsCount}</p>
        </div>
      </div>

      {loadingDraft ? <p className="text-sm text-muted-foreground">Cargando borrador...</p> : null}

      <div className="rounded-md border border-border bg-card p-4 space-y-4">
        <div className="grid gap-3 md:grid-cols-5">
          <label className="text-sm">
            Bodega origen
            <SearchableSelect className="mt-1" value={header.bodega_origen_id} onChange={(next) => setHeader((prev) => ({ ...prev, bodega_origen_id: next }))} options={bodegaOptions} ariaLabel="Bodega origen masivo" placeholder="Buscar bodega..." emptyText="No hay bodegas coincidentes" />
          </label>
          <label className="text-sm">
            Bodega destino
            <SearchableSelect className="mt-1" value={header.bodega_destino_id} onChange={(next) => setHeader((prev) => ({ ...prev, bodega_destino_id: next }))} options={bodegaOptions} ariaLabel="Bodega destino masivo" placeholder="Buscar bodega..." emptyText="No hay bodegas coincidentes" />
          </label>
          <label className="text-sm">
            Motivo operativo
            <input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={header.motivo} onChange={(event) => setHeader((prev) => ({ ...prev, motivo: event.target.value }))} />
          </label>
          <label className="text-sm">
            Referencia operativa
            <input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={header.referencia_operativa} onChange={(event) => setHeader((prev) => ({ ...prev, referencia_operativa: event.target.value }))} />
          </label>
          <label className="text-sm">
            Observaciones
            <input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={header.observaciones} onChange={(event) => setHeader((prev) => ({ ...prev, observaciones: event.target.value }))} />
          </label>
        </div>

        {headerErrors.length > 0 ? (
          <div className="rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive">
            {headerErrors.join(' ')}
          </div>
        ) : null}

        <div className="rounded-md border border-border bg-muted/20 p-3">
          <div className="flex flex-wrap items-center gap-2">
            <Button type="button" variant="outline" onClick={() => addRows(1)}>Agregar 1 linea</Button>
            <Button type="button" variant="outline" onClick={() => addRows(5)}>Agregar 5 lineas</Button>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            Usa esta grilla para corregir productos y cantidades del borrador antes de confirmar el traslado definitivo.
          </p>
        </div>

        <div className="overflow-x-auto rounded-md border border-border">
          <table className="min-w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="px-3 py-2 text-left font-medium">#</th>
                <th className="px-3 py-2 text-left font-medium">Producto</th>
                <th className="px-3 py-2 text-left font-medium">Cantidad</th>
                <th className="px-3 py-2 text-left font-medium">Validacion</th>
                <th className="px-3 py-2 text-left font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => {
                const diagnostics = diagnosticsById.get(row.id)
                return (
                  <tr
                    key={row.id}
                    className={cn('border-t border-border align-top', diagnostics?.valid ? 'bg-background' : 'bg-destructive/5')}
                  >
                    <td className="px-3 py-3 text-muted-foreground">{index + 1}</td>
                    <td className="min-w-80 px-3 py-3">
                      <SearchableSelect
                        value={row.producto_id}
                        onChange={(next) => updateRow(row.id, 'producto_id', next)}
                        onSearchChange={(next) => { void searchProductos(next) }}
                        options={productoOptions}
                        ariaLabel={`Producto traslado masivo ${index + 1}`}
                        placeholder="Buscar producto..."
                        emptyText="No hay productos coincidentes"
                        loading={loadingProductos}
                      />
                    </td>
                    <td className="min-w-40 px-3 py-3">
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={row.cantidad}
                        onChange={(event) => updateRow(row.id, 'cantidad', event.target.value)}
                        className="w-full rounded-md border border-input bg-background px-3 py-2"
                      />
                    </td>
                    <td className="min-w-64 px-3 py-3">
                      {diagnostics?.valid ? (
                        <span className="text-muted-foreground">Linea valida</span>
                      ) : (
                        <div className="rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive">
                          {diagnostics.errors.join(' ')}
                        </div>
                      )}
                    </td>
                    <td className="px-3 py-3">
                      <div className="flex flex-wrap gap-2">
                        <Button type="button" variant="outline" size="sm" onClick={() => duplicateRow(row.id)}>Duplicar</Button>
                        <Button type="button" variant="outline" size="sm" onClick={() => removeRow(row.id)}>Quitar</Button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" disabled={savingMode !== null} onClick={() => { void handleSubmit('BORRADOR') }}>
            {savingMode === 'BORRADOR' ? 'Guardando...' : 'Guardar borrador'}
          </Button>
          <Button type="button" disabled={savingMode !== null} onClick={() => { void handleSubmit('CONFIRMADO') }}>
            {savingMode === 'CONFIRMADO' ? 'Confirmando...' : 'Confirmar traslado masivo'}
          </Button>
        </div>
      </div>

      {lastDocument ? (
        <div className="rounded-md border border-border bg-card p-4">
          <h3 className="text-base font-semibold">Ultimo documento generado</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            {lastDocument.numero} | {lastDocument.estado} | {lastDocument.items?.length || 0} lineas | referencia {lastDocument.referencia}
          </p>
        </div>
      ) : null}

      <div className="rounded-md border border-border bg-card p-4">
        <h3 className="text-base font-semibold">Ultimos traslados masivos</h3>
        <div className="mt-3 grid gap-3 md:grid-cols-4">
          <label className="text-sm">
            Buscar
            <input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={filters.q} onChange={(event) => setFilters((prev) => ({ ...prev, q: event.target.value }))} placeholder="Numero, motivo o referencia" />
          </label>
          <label className="text-sm">
            Estado
            <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={filters.estado} onChange={(event) => setFilters((prev) => ({ ...prev, estado: event.target.value }))}>
              <option value="">Todos</option>
              <option value="BORRADOR">Borrador</option>
              <option value="CONFIRMADO">Confirmado</option>
            </select>
          </label>
          <label className="text-sm">
            Desde
            <input type="date" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={filters.desde} onChange={(event) => setFilters((prev) => ({ ...prev, desde: event.target.value }))} />
          </label>
          <label className="text-sm">
            Hasta
            <input type="date" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={filters.hasta} onChange={(event) => setFilters((prev) => ({ ...prev, hasta: event.target.value }))} />
          </label>
        </div>
        <div className="mt-3 flex gap-2">
          <Button type="button" variant="outline" onClick={() => { void loadRecentDocuments(filters) }} disabled={loadingList}>
            {loadingList ? 'Consultando...' : 'Aplicar filtros'}
          </Button>
        </div>
        {recentDocuments.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">Todavia no hay documentos masivos recientes.</p>
        ) : (
          <div className="mt-3 space-y-2">
            {recentDocuments.map((documento) => (
              <div key={documento.id} className="flex flex-col gap-2 rounded-md border border-border px-3 py-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="text-sm font-medium">{documento.numero}</p>
                  <p className="text-xs text-muted-foreground">
                    {documento.estado} | {documento.bodega_origen_nombre || '-'} a {documento.bodega_destino_nombre || '-'} | {documento.items?.length || 0} lineas
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button type="button" variant="outline" size="sm" disabled={duplicatingId === documento.id} onClick={() => { void handleDuplicate(documento.id) }}>
                    {duplicatingId === documento.id ? 'Duplicando...' : 'Duplicar'}
                  </Button>
                  <Link to={`/inventario/traslados-masivos/${documento.id}`} className={cn(buttonVariants({ variant: 'outline', size: 'sm' }))}>
                    Ver detalle
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

export default InventarioTrasladosMasivosPage

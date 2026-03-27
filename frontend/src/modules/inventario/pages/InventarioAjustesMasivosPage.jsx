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
    bodega_id: '',
    stock_objetivo: '',
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

function InventarioAjustesMasivosPage() {
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
  const initialProductoId = searchParams.get('producto_id') || ''
  const initialBodegaId = searchParams.get('bodega_id') || ''
  const initialStockObjetivo = searchParams.get('stock_objetivo') || ''
  const [header, setHeader] = useState({ motivo: '', referencia_operativa: '', observaciones: '' })
  const [rows, setRows] = useState([
    {
      ...buildRow(),
      producto_id: initialProductoId,
      bodega_id: initialBodegaId,
      stock_objetivo: initialStockObjetivo,
    },
  ])
  const bulkImportEndpoint = `${inventarioApi.endpoints.ajustesMasivos}bulk_import/`
  const bulkTemplateEndpoint = `${inventarioApi.endpoints.ajustesMasivos}bulk_template/`

  const loadRecentDocuments = useCallback(async (nextFilters) => {
    setLoadingList(true)
    try {
      const documentosData = await inventarioApi.getPaginated(inventarioApi.endpoints.ajustesMasivos, {
        page_size: 5,
        ...(nextFilters.estado ? { estado: nextFilters.estado } : {}),
        ...(nextFilters.desde ? { desde: nextFilters.desde } : {}),
        ...(nextFilters.hasta ? { hasta: nextFilters.hasta } : {}),
        ...(nextFilters.q ? { q: nextFilters.q } : {}),
      })
      setRecentDocuments(documentosData.results || [])
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los ajustes masivos.' }))
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
        toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los datos del ajuste masivo.' }))
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
        const data = await inventarioApi.getOne(inventarioApi.endpoints.ajustesMasivos, draftId)
        if (data.estado !== 'BORRADOR') {
          toast.error('Solo se pueden editar ajustes masivos en borrador.')
          navigate(`/inventario/ajustes-masivos/${draftId}`, { replace: true })
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
        })
        setRows(
          (data.items || []).map((item, index) => ({
            id: `${item.id || index}`,
            producto_id: String(item.producto || ''),
            bodega_id: item.bodega ? String(item.bodega) : '',
            stock_objetivo: String(item.stock_objetivo ?? ''),
          })),
        )
        setLastDocument(data)
      } catch (error) {
        toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar el borrador del ajuste masivo.' }))
      } finally {
        setLoadingDraft(false)
      }
    }

    void loadDraft()
  }, [draftId, navigate])

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
      const key = `${row.producto_id || ''}|${row.bodega_id || ''}`
      if (!row.producto_id) {
        return
      }
      duplicates.set(key, (duplicates.get(key) || 0) + 1)
    })

    return rows.map((row) => {
      const errors = []
      if (!row.producto_id) {
        errors.push('Debe seleccionar un producto.')
      }
      if (row.stock_objetivo === '') {
        errors.push('Debe informar stock objetivo.')
      } else if (Number(row.stock_objetivo) < 0) {
        errors.push('El stock objetivo no puede ser negativo.')
      }
      const key = `${row.producto_id || ''}|${row.bodega_id || ''}`
      if (row.producto_id && (duplicates.get(key) || 0) > 1) {
        errors.push('La combinacion producto y bodega no puede repetirse.')
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
  const applyBodegaToEmptyRows = (bodegaId) => {
    if (!bodegaId) {
      return
    }
    setRows((prev) => prev.map((row) => (row.bodega_id ? row : { ...row, bodega_id: bodegaId })))
  }

  const handleSubmit = async (mode = 'CONFIRMADO') => {
    const referencia = buildReference(header)
    const items = rows
      .filter((row) => row.producto_id && row.stock_objetivo !== '')
      .map((row) => ({
        producto_id: row.producto_id,
        bodega_id: row.bodega_id || null,
        stock_objetivo: row.stock_objetivo,
      }))

    if (!header.motivo.trim()) {
      toast.error('Debe informar el motivo operativo del ajuste masivo.')
      return
    }
    if (invalidRowsCount > 0) {
      toast.error('Corrige las lineas con error antes de guardar o confirmar el borrador.')
      return
    }
    if (items.length === 0) {
      toast.error('Debe informar al menos una linea valida.')
      return
    }

    setSavingMode(mode)
    try {
      const payload = {
        referencia,
        motivo: header.motivo,
        observaciones: header.observaciones,
        items,
      }
      let data = null
      if (draftId) {
        const draft = await inventarioApi.patchOne(inventarioApi.endpoints.ajustesMasivos, draftId, payload)
        data = mode === 'CONFIRMADO'
          ? await inventarioApi.executeDetailAction(inventarioApi.endpoints.ajustesMasivos, draft.id, 'confirmar')
          : draft
      } else {
        data = await inventarioApi.postOne(inventarioApi.endpoints.ajustesMasivos, {
          ...payload,
          estado: mode,
        })
      }
      setLastDocument(data)
      await loadRecentDocuments(filters)
      if (mode === 'BORRADOR') {
        toast.success(draftId ? 'Borrador de ajuste masivo actualizado correctamente.' : 'Borrador de ajuste masivo guardado correctamente.')
        if (!draftId) {
          navigate(`/inventario/ajustes-masivos?draft=${data.id}`, { replace: true })
        }
      } else {
        toast.success('Ajuste masivo confirmado correctamente.')
        navigate(`/inventario/ajustes-masivos/${data.id}`, { replace: true })
      }
      if (!draftId && mode === 'BORRADOR') {
        setHeader({ motivo: '', referencia_operativa: '', observaciones: '' })
        setRows([buildRow()])
      }
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: mode === 'BORRADOR' ? 'No se pudo guardar el borrador del ajuste masivo.' : 'No se pudo confirmar el ajuste masivo.' }))
    } finally {
      setSavingMode(null)
    }
  }

  const handleDuplicate = async (documentoId) => {
    setDuplicatingId(documentoId)
    try {
      const data = await inventarioApi.executeDetailAction(inventarioApi.endpoints.ajustesMasivos, documentoId, 'duplicar')
      setLastDocument(data)
      await loadRecentDocuments(filters)
      toast.success('Borrador de ajuste masivo duplicado correctamente.')
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo duplicar el ajuste masivo.' }))
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
          <h2 className="text-2xl font-semibold">{draftId ? 'Editar borrador de ajuste masivo' : 'Ajuste masivo de inventario'}</h2>
          <p className="text-sm text-muted-foreground">
            {draftId ? 'Actualiza el borrador antes de confirmarlo y dejar trazabilidad final.' : 'Confirma un documento con multiples regularizaciones por producto y bodega.'}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <BulkImportButton
            endpoint={bulkImportEndpoint}
            templateEndpoint={bulkTemplateEndpoint}
            previewBeforeImport
            previewTitle="Confirmar importacion de ajustes masivos"
            onCompleted={(data) => { void handleBulkImportCompleted(data) }}
          />
          <Link to={draftId ? `/inventario/ajustes-masivos/${draftId}` : '/inventario/ajustes'} className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
            {draftId ? 'Volver al detalle' : 'Volver a ajustes simples'}
          </Link>
        </div>
      </div>

      <div className="rounded-md border border-border bg-card p-4">
        <p className="text-sm text-muted-foreground">
          La importacion por XLSX o CSV crea un borrador validado. El stock no se mueve hasta confirmar el documento desde su detalle.
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
        <div className="grid gap-3 md:grid-cols-3">
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

        <div className="rounded-md border border-border bg-muted/20 p-3">
          <div className="flex flex-wrap items-center gap-2">
            <Button type="button" variant="outline" onClick={() => addRows(1)}>Agregar 1 linea</Button>
            <Button type="button" variant="outline" onClick={() => addRows(5)}>Agregar 5 lineas</Button>
            <Button
              type="button"
              variant="outline"
              disabled={!rows.some((row) => row.bodega_id)}
              onClick={() => applyBodegaToEmptyRows(rows.find((row) => row.bodega_id)?.bodega_id)}
            >
              Completar bodega en vacias
            </Button>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            La grilla esta pensada para correcciones rapidas de borradores importados. Puedes duplicar filas y completar bodegas faltantes en lote.
          </p>
        </div>

        <div className="overflow-x-auto rounded-md border border-border">
          <table className="min-w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="px-3 py-2 text-left font-medium">#</th>
                <th className="px-3 py-2 text-left font-medium">Producto</th>
                <th className="px-3 py-2 text-left font-medium">Bodega</th>
                <th className="px-3 py-2 text-left font-medium">Stock objetivo</th>
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
                    <td className="min-w-72 px-3 py-3">
                      <SearchableSelect
                        value={row.producto_id}
                        onChange={(next) => updateRow(row.id, 'producto_id', next)}
                        onSearchChange={(next) => { void searchProductos(next) }}
                        options={productoOptions}
                        ariaLabel={`Producto ajuste masivo ${index + 1}`}
                        placeholder="Buscar producto..."
                        emptyText="No hay productos coincidentes"
                        loading={loadingProductos}
                      />
                    </td>
                    <td className="min-w-56 px-3 py-3">
                      <SearchableSelect
                        value={row.bodega_id}
                        onChange={(next) => updateRow(row.id, 'bodega_id', next)}
                        options={bodegaOptions}
                        ariaLabel={`Bodega ajuste masivo ${index + 1}`}
                        placeholder="Buscar bodega..."
                        emptyText="No hay bodegas coincidentes"
                      />
                    </td>
                    <td className="min-w-40 px-3 py-3">
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={row.stock_objetivo}
                        onChange={(event) => updateRow(row.id, 'stock_objetivo', event.target.value)}
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
            {savingMode === 'CONFIRMADO' ? 'Confirmando...' : 'Confirmar ajuste masivo'}
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
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold">Ultimos ajustes masivos</h3>
        </div>
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
                  <p className="text-xs text-muted-foreground">{documento.estado} | {documento.motivo} | {documento.items?.length || 0} lineas</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button type="button" variant="outline" size="sm" disabled={duplicatingId === documento.id} onClick={() => { void handleDuplicate(documento.id) }}>
                    {duplicatingId === documento.id ? 'Duplicando...' : 'Duplicar'}
                  </Button>
                  <Link to={`/inventario/ajustes-masivos/${documento.id}`} className={cn(buttonVariants({ variant: 'outline', size: 'sm' }))}>
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

export default InventarioAjustesMasivosPage

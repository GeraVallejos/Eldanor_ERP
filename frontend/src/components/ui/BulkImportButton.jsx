import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import { downloadBulkImportErrorsFile } from '@/modules/shared/exports/downloadBulkImportErrorsFile'

function inferTemplateFileName(templateEndpoint) {
  const segments = String(templateEndpoint || '')
    .split('/')
    .map((segment) => segment.trim())
    .filter(Boolean)

  if (segments.length === 0) {
    return 'plantilla_importacion.xlsx'
  }

  const bulkTemplateIndex = segments.lastIndexOf('bulk_template')
  const candidateSegments = bulkTemplateIndex > 0 ? segments.slice(0, bulkTemplateIndex) : segments
  const rawSegment = [...candidateSegments]
    .reverse()
    .find((segment) => !/^\d+$/.test(segment) && !/^[0-9a-f-]{8,}$/i.test(segment))
    || candidateSegments.at(-1)
  const normalizedSegment = String(rawSegment || 'importacion')
    .replace(/-/g, '_')
    .toLowerCase()

  return `plantilla_${normalizedSegment || 'importacion'}.xlsx`
}

function BulkImportButton({
  endpoint,
  templateEndpoint,
  onCompleted,
  disabled = false,
  previewBeforeImport = false,
  previewTitle = 'Confirmar importacion',
  summaryMode = 'mutations',
}) {
  const inputRef = useRef(null)
  const menuRef = useRef(null)
  const [isOpen, setIsOpen] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [downloadingTemplate, setDownloadingTemplate] = useState(false)
  const [previewData, setPreviewData] = useState(null)
  const [pendingFile, setPendingFile] = useState(null)

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (!menuRef.current) {
        return
      }
      if (!menuRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const openPicker = () => {
    if (disabled || uploading) {
      return
    }
    setIsOpen(false)
    inputRef.current?.click()
  }

  const handleDownloadTemplate = async () => {
    if (!templateEndpoint || downloadingTemplate || disabled) {
      return
    }

    setDownloadingTemplate(true)
    try {
      const response = await api.get(templateEndpoint, {
        responseType: 'blob',
        suppressGlobalErrorToast: true,
      })

      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      const disposition = String(response.headers?.['content-disposition'] || '')
      const fileNameMatch = disposition.match(/filename="?([^";]+)"?/i)
      const fileName = fileNameMatch?.[1] || inferTemplateFileName(templateEndpoint)

      link.href = url
      link.setAttribute('download', fileName)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
      setIsOpen(false)
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo descargar la plantilla.' }))
    } finally {
      setDownloadingTemplate(false)
    }
  }

  const executeUpload = async (file, { dryRun = false } = {}) => {
    const formData = new FormData()
    formData.append('file', file)
    if (dryRun) {
      formData.append('dry_run', 'true')
    }

    const { data } = await api.post(endpoint, formData, {
      suppressGlobalErrorToast: true,
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return data
  }

  const processCompletedUpload = async (data) => {
      const created = Number(data?.created || 0)
      const updated = Number(data?.updated || 0)
      const errorCount = Array.isArray(data?.errors) ? data.errors.length : 0
      const warningCount = Array.isArray(data?.warnings) ? data.warnings.length : 0
      const successfulRows = Number(data?.successful_rows ?? created + updated)

      if (successfulRows > 0) {
        if (summaryMode === 'rows') {
          toast.success(
            `Carga finalizada: ${successfulRows} filas procesadas${errorCount ? `, ${errorCount} con error` : ''}${warningCount ? `, ${warningCount} con advertencia` : ''}.`,
          )
        } else {
          toast.success(
            `Carga finalizada: ${created} creados, ${updated} actualizados${errorCount ? `, ${errorCount} con error` : ''}${warningCount ? `, ${warningCount} con advertencia` : ''}.`,
          )
        }
      } else if (errorCount > 0) {
        toast.error(`No se pudo importar ninguna fila. Se detectaron ${errorCount} errores.`)
      } else {
        toast.info('El archivo no contenia filas para procesar.')
      }

      if (errorCount > 0) {
        const firstError = data.errors[0]
        toast.warning(`Primera fila con error (linea ${firstError?.line || '-'}): ${firstError?.detail || 'Error desconocido'}`)
        await downloadBulkImportErrorsFile({
          errors: data.errors,
          endpoint,
        })
      }

      if (warningCount > 0) {
        const firstWarning = data.warnings[0]
        toast.warning(`Advertencia de carga (linea ${firstWarning?.line || '-'}): ${firstWarning?.detail || 'Revise el archivo importado.'}`)
      }

      if (typeof onCompleted === 'function') {
        onCompleted(data)
      }
  }

  const handleConfirmImport = async () => {
    if (!pendingFile) {
      setPreviewData(null)
      return
    }

    setUploading(true)
    try {
      const data = await executeUpload(pendingFile)
      await processCompletedUpload(data)
      setPreviewData(null)
      setPendingFile(null)
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo ejecutar la carga masiva.' }))
    } finally {
      setUploading(false)
      if (inputRef.current) {
        inputRef.current.value = ''
      }
    }
  }

  const handleChange = async (event) => {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }

    setUploading(true)
    try {
      if (previewBeforeImport) {
        const data = await executeUpload(file, { dryRun: true })
        setPendingFile(file)
        setPreviewData(data)
        return
      }

      const data = await executeUpload(file)
      await processCompletedUpload(data)
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo ejecutar la carga masiva.' }))
    } finally {
      setUploading(false)
      if (inputRef.current) {
        inputRef.current.value = ''
      }
    }
  }

  const previewSuccessfulRows = Number(previewData?.successful_rows ?? Number(previewData?.created || 0) + Number(previewData?.updated || 0))
  const previewErrorCount = Array.isArray(previewData?.errors) ? previewData.errors.length : 0
  const previewWarningCount = Array.isArray(previewData?.warnings) ? previewData.warnings.length : 0
  const canConfirmPreview = previewSuccessfulRows > 0

  const previewDescription = previewData ? (
    <div className="space-y-2">
      {canConfirmPreview ? (
        <>
          <p>Se detectaron {previewSuccessfulRows} filas validas para procesar.</p>
          {summaryMode === 'rows' ? (
            <p>Estas filas se compararan contra el stock actual al confirmar el documento.</p>
          ) : (
            <p>Se crearan {previewData.created || 0} registros y se actualizaran {previewData.updated || 0}.</p>
          )}
        </>
      ) : (
        <p>
          {previewErrorCount > 0
            ? `No se detectaron filas validas para importar. Se encontraron ${previewErrorCount} errores en el archivo.`
            : 'El archivo no contiene filas validas para importar.'}
        </p>
      )}
      {Array.isArray(previewData.errors) && previewData.errors.length > 0 ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-amber-950">
          <p>
            {canConfirmPreview
              ? `Ademas, ${previewErrorCount} filas quedaran con error y no se importaran.`
              : `Detalle de errores detectados: ${previewErrorCount} fila(s) requieren correccion.`}
          </p>
          <div className="mt-2 space-y-1">
            {previewData.errors.slice(0, 3).map((row) => (
              <p key={`${row?.line || 'sin-linea'}-${row?.sku || 'sin-sku'}`} className="text-xs">
                Fila {row?.line || '-'}: {row?.detail || 'Error desconocido'}
              </p>
            ))}
          </div>
          {previewData.errors.length > 3 ? (
            <p className="mt-2 text-xs">
              Se muestran 3 errores de muestra. El resto seguira disponible en el reporte de errores final.
            </p>
          ) : null}
        </div>
      ) : null}
      {Array.isArray(previewData.warnings) && previewData.warnings.length > 0 ? (
        <div className="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-sky-950">
          <p>Advertencias detectadas: {previewWarningCount} fila(s) validas requieren atencion.</p>
          <div className="mt-2 space-y-1">
            {previewData.warnings.slice(0, 3).map((row) => (
              <p key={`${row?.code || 'warning'}-${row?.line || 'sin-linea'}-${row?.sku || 'sin-sku'}`} className="text-xs">
                Fila {row?.line || '-'}: {row?.detail || 'Advertencia sin detalle'}
              </p>
            ))}
          </div>
          {previewData.warnings.length > 3 ? (
            <p className="mt-2 text-xs">
              Se muestran 3 advertencias de muestra. Revise el archivo antes de confirmar la importacion.
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  ) : null

  return (
    <div ref={menuRef} className="relative">
      <input
        ref={inputRef}
        type="file"
        accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        className="hidden"
        onChange={handleChange}
      />
      <Button
        variant="outline"
        size="sm"
        className="h-9 px-3 text-xs"
        onClick={() => setIsOpen((prev) => !prev)}
        disabled={disabled || uploading || downloadingTemplate}
      >
        {uploading ? 'Cargando...' : downloadingTemplate ? 'Descargando...' : 'Importar'}
      </Button>

      {isOpen ? (
        <div className="absolute right-0 z-20 mt-1 w-56 rounded-md border border-border bg-popover p-1 shadow-md">
          <button
            type="button"
            className="block w-full rounded px-2 py-2 text-left text-xs hover:bg-muted"
            onClick={handleDownloadTemplate}
            disabled={downloadingTemplate}
          >
            Descargar plantilla XLSX
          </button>
          <button
            type="button"
            className="mt-1 block w-full rounded px-2 py-2 text-left text-xs hover:bg-muted"
            onClick={openPicker}
            disabled={uploading}
          >
            Cargar archivo CSV/XLSX
          </button>
        </div>
      ) : null}

      <ConfirmDialog
        open={Boolean(previewData)}
        title={previewTitle}
        description={previewDescription}
        confirmLabel="Importar archivo"
        cancelLabel={canConfirmPreview ? 'Cancelar' : 'Cerrar'}
        hideConfirm={!canConfirmPreview}
        loading={uploading}
        onCancel={() => {
          if (!uploading) {
            setPreviewData(null)
            setPendingFile(null)
            if (inputRef.current) {
              inputRef.current.value = ''
            }
          }
        }}
        onConfirm={handleConfirmImport}
      />
    </div>
  )
}

export default BulkImportButton

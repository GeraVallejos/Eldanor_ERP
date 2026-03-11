import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'

function BulkImportButton({ endpoint, templateEndpoint, onCompleted, disabled = false }) {
  const inputRef = useRef(null)
  const menuRef = useRef(null)
  const [isOpen, setIsOpen] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [downloadingTemplate, setDownloadingTemplate] = useState(false)

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
      const fileName = fileNameMatch?.[1] || 'plantilla_importacion.xlsx'

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

  const handleChange = async (event) => {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }

    const formData = new FormData()
    formData.append('file', file)

    setUploading(true)
    try {
      const { data } = await api.post(endpoint, formData, {
        suppressGlobalErrorToast: true,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      const created = Number(data?.created || 0)
      const updated = Number(data?.updated || 0)
      const errorCount = Array.isArray(data?.errors) ? data.errors.length : 0
      const successfulRows = Number(data?.successful_rows ?? created + updated)

      if (successfulRows > 0) {
        toast.success(
          `Carga finalizada: ${created} creados, ${updated} actualizados${errorCount ? `, ${errorCount} con error` : ''}.`,
        )
      } else if (errorCount > 0) {
        toast.error(`No se pudo importar ninguna fila. Se detectaron ${errorCount} errores.`)
      } else {
        toast.info('El archivo no contenia filas para procesar.')
      }

      if (errorCount > 0) {
        const firstError = data.errors[0]
        toast.warning(`Primera fila con error (linea ${firstError?.line || '-'}): ${firstError?.detail || 'Error desconocido'}`)
      }

      if (typeof onCompleted === 'function') {
        onCompleted(data)
      }
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo ejecutar la carga masiva.' }))
    } finally {
      setUploading(false)
      if (inputRef.current) {
        inputRef.current.value = ''
      }
    }
  }

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
    </div>
  )
}

export default BulkImportButton

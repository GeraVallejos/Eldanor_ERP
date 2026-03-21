import { getChileDateSuffix } from '@/lib/dateTimeFormat'
import { downloadExcelFile } from '@/modules/shared/exports/downloadExcelFile'

function sanitizeSegment(value, fallback) {
  const normalized = String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')

  return normalized || fallback
}

export async function downloadBulkImportErrorsFile({ errors, endpoint, fileName } = {}) {
  const rows = Array.isArray(errors) ? errors : []
  if (!rows.length) {
    return
  }

  const resourceSegment = sanitizeSegment(endpoint, 'importacion')
  const exportName = fileName || `errores_${resourceSegment}_${getChileDateSuffix()}.xlsx`

  await downloadExcelFile({
    sheetName: 'Errores importacion',
    fileName: exportName,
    columns: [
      { header: 'Linea', key: 'line', width: 12 },
      { header: 'Detalle', key: 'detail', width: 80 },
      { header: 'Referencia', key: 'reference', width: 28 },
      { header: 'Nombre', key: 'nombre', width: 28 },
      { header: 'SKU', key: 'sku', width: 24 },
      { header: 'Tipo documento', key: 'tipo_documento', width: 24 },
    ],
    rows: rows.map((row) => ({
      line: row?.line ?? '',
      detail: row?.detail ?? '',
      reference: row?.referencia ?? '',
      nombre: row?.nombre ?? '',
      sku: row?.sku ?? '',
      tipo_documento: row?.tipo_documento ?? '',
    })),
  })
}

export default downloadBulkImportErrorsFile

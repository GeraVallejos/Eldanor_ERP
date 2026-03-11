import { pdf } from '@react-pdf/renderer'
import { createElement } from 'react'
import SimpleTablePdfDocument from '@/modules/shared/exports/SimpleTablePdfDocument'

export async function downloadSimpleTablePdf({ title, headers, rows, fileName }) {
  const blob = await pdf(createElement(SimpleTablePdfDocument, { title, headers, rows })).toBlob()

  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName || 'reporte.pdf'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

export async function downloadExcelFile({ sheetName, fileName, columns, rows }) {
  const ExcelJS = await import('exceljs')
  const workbook = new ExcelJS.Workbook()
  const sheet = workbook.addWorksheet(sheetName || 'Reporte')

  sheet.columns = Array.isArray(columns) ? columns : []
  if (Array.isArray(columns)) {
    columns.forEach((column, index) => {
      const worksheetColumn = sheet.getColumn(index + 1)
      if (column?.numFmt) {
        worksheetColumn.numFmt = column.numFmt
      }
      if (column?.alignment) {
        worksheetColumn.alignment = column.alignment
      }
    })
  }

  if (Array.isArray(rows)) {
    rows.forEach((row) => {
      sheet.addRow(row)
    })
  }

  const buffer = await workbook.xlsx.writeBuffer()
  const blob = new Blob([buffer], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })

  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName || 'reporte.xlsx'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

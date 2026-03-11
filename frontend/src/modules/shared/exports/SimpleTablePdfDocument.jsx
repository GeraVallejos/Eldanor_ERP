import { Document, Page, StyleSheet, Text, View } from '@react-pdf/renderer'

const styles = StyleSheet.create({
  page: { padding: 24, fontSize: 10, fontFamily: 'Helvetica' },
  title: { fontSize: 14, marginBottom: 12, fontWeight: 'bold' },
  headerRow: { flexDirection: 'row', borderBottomWidth: 1, borderBottomColor: '#d1d5db', paddingBottom: 4 },
  row: { flexDirection: 'row', borderBottomWidth: 1, borderBottomColor: '#f3f4f6', paddingVertical: 4 },
  cell: { flex: 1, paddingRight: 6 },
  headerText: { fontWeight: 'bold' },
})

function normalizeRows(rows) {
  if (!Array.isArray(rows)) {
    return []
  }

  return rows.map((row) => (Array.isArray(row) ? row : []))
}

function SimpleTablePdfDocument({ title, headers, rows }) {
  const safeHeaders = Array.isArray(headers) ? headers : []
  const safeRows = normalizeRows(rows)

  return (
    <Document>
      <Page size="A4" style={styles.page}>
        <Text style={styles.title}>{title || 'Reporte'}</Text>

        <View style={styles.headerRow}>
          {safeHeaders.map((header) => (
            <View style={styles.cell} key={`header-${header}`}>
              <Text style={styles.headerText}>{String(header || '')}</Text>
            </View>
          ))}
        </View>

        {safeRows.map((row, rowIndex) => (
          <View style={styles.row} key={`row-${rowIndex}`}>
            {safeHeaders.map((_, colIndex) => (
              <View style={styles.cell} key={`cell-${rowIndex}-${colIndex}`}>
                <Text>{String(row[colIndex] ?? '')}</Text>
              </View>
            ))}
          </View>
        ))}
      </Page>
    </Document>
  )
}

export default SimpleTablePdfDocument

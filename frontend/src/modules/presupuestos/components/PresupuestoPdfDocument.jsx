import { Document, Page, StyleSheet, Text, View } from '@react-pdf/renderer'
import DocumentHeaderBrand from '@/modules/shared/documents/DocumentHeaderBrand'

const styles = StyleSheet.create({
  page: {
    padding: 28,
    fontSize: 10,
    color: '#111827',
  },
  rowBetween: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 12,
    marginBottom: 4,
  },
  infoBlock: {
    flexShrink: 1,
  },
  brandBlock: {
    width: 130,
  },
  title: {
    fontSize: 20,
    fontWeight: 700,
    marginBottom: 6,
  },
  muted: {
    color: '#6B7280',
    fontSize: 9,
    marginTop: 2,
  },
  card: {
    borderWidth: 1,
    borderColor: '#E5E7EB',
    borderRadius: 6,
    padding: 10,
    marginTop: 12,
  },
  cardTitle: {
    fontSize: 11,
    fontWeight: 700,
    marginBottom: 6,
  },
  tableHeader: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderBottomColor: '#D1D5DB',
    paddingBottom: 5,
    marginTop: 6,
  },
  tableRow: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
    paddingVertical: 5,
  },
  colDescription: {
    flex: 2.8,
    paddingRight: 8,
  },
  colQty: {
    flex: 0.8,
    textAlign: 'right',
  },
  colPrice: {
    flex: 1,
    textAlign: 'right',
  },
  colDiscount: {
    flex: 0.9,
    textAlign: 'right',
  },
  colTax: {
    flex: 0.9,
    textAlign: 'right',
  },
  colTotal: {
    flex: 1.1,
    textAlign: 'right',
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    marginTop: 3,
  },
  summaryLabel: {
    width: 120,
    textAlign: 'right',
    color: '#6B7280',
  },
  summaryValue: {
    width: 90,
    textAlign: 'right',
    fontWeight: 700,
  },
  totalLabel: {
    width: 120,
    textAlign: 'right',
    fontWeight: 700,
  },
  totalValue: {
    width: 90,
    textAlign: 'right',
    fontSize: 12,
    fontWeight: 700,
  },
})

function formatMoney(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) {
    return '0'
  }

  return Math.round(num).toLocaleString('es-CL')
}

function formatDate(value) {
  if (!value) {
    return '-'
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return String(value)
  }

  return date.toLocaleDateString('es-CL')
}

function PresupuestoPdfDocument({ presupuesto, items, empresa, cliente }) {
  const safeItems = Array.isArray(items) ? items : []

  return (
    <Document>
      <Page size="A4" style={styles.page}>
        <View style={styles.rowBetween}>
          <View style={styles.infoBlock}>
            <Text style={styles.title}>Presupuesto</Text>
            <Text style={styles.muted}>Nro: {presupuesto?.numero || '-'}</Text>
            <Text style={styles.muted}>Estado: {presupuesto?.estado || '-'}</Text>
          </View>
          <DocumentHeaderBrand
            style={styles.brandBlock}
            logoSrc={empresa?.logo || null}
            companyName={empresa?.nombre || 'Empresa'}
          />
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Datos generales</Text>
          <Text>Fecha emision: {formatDate(presupuesto?.fecha)}</Text>
          <Text>Vencimiento: {formatDate(presupuesto?.fecha_vencimiento)}</Text>
          <Text>Cliente: {cliente?.nombre || '-'}</Text>
          <Text>RUT: {cliente?.rut || '-'}</Text>
          <Text>Email: {cliente?.email || '-'}</Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Detalle</Text>
          <View style={styles.tableHeader}>
            <Text style={styles.colDescription}>Descripcion</Text>
            <Text style={styles.colQty}>Cant.</Text>
            <Text style={styles.colPrice}>P. Unit</Text>
            <Text style={styles.colDiscount}>Desc %</Text>
            <Text style={styles.colTax}>IVA %</Text>
            <Text style={styles.colTotal}>Total</Text>
          </View>

          {safeItems.length === 0 ? (
            <View style={styles.tableRow}>
              <Text style={styles.colDescription}>Sin items cargados.</Text>
            </View>
          ) : (
            safeItems.map((item) => (
              <View key={String(item.id)} style={styles.tableRow}>
                <Text style={styles.colDescription}>{item.descripcion || '-'}</Text>
                <Text style={styles.colQty}>{formatMoney(item.cantidad || 0)}</Text>
                <Text style={styles.colPrice}>{formatMoney(item.precio_unitario || 0)}</Text>
                <Text style={styles.colDiscount}>{formatMoney(item.descuento || 0)}</Text>
                <Text style={styles.colTax}>{formatMoney(item.impuesto_porcentaje || 0)}</Text>
                <Text style={styles.colTotal}>{formatMoney(item.total || 0)}</Text>
              </View>
            ))
          )}
        </View>

        <View style={styles.card}>
          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>Subtotal</Text>
            <Text style={styles.summaryValue}>{formatMoney(presupuesto?.subtotal || 0)}</Text>
          </View>
          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>Descuento</Text>
            <Text style={styles.summaryValue}>{formatMoney(presupuesto?.descuento || 0)}</Text>
          </View>
          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>Impuestos</Text>
            <Text style={styles.summaryValue}>{formatMoney(presupuesto?.impuesto_total || 0)}</Text>
          </View>
          <View style={styles.summaryRow}>
            <Text style={styles.totalLabel}>Total</Text>
            <Text style={styles.totalValue}>{formatMoney(presupuesto?.total || 0)}</Text>
          </View>
        </View>

        {presupuesto?.observaciones ? (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Observaciones</Text>
            <Text>{presupuesto.observaciones}</Text>
          </View>
        ) : null}
      </Page>
    </Document>
  )
}

export default PresupuestoPdfDocument

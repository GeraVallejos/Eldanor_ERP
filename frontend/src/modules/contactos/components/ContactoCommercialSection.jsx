import { formatCurrencyCLP } from '@/lib/numberFormat'
import { DetailRow, InfoCard } from '@/modules/contactos/components/ContactoDetailPrimitives'

function formatMoney(value) {
  return formatCurrencyCLP(value ?? 0)
}

function ContactoCommercialSection({ cliente, proveedor }) {
  const hasCliente = Boolean(cliente)
  const hasProveedor = Boolean(proveedor)

  return (
    <InfoCard title="Ficha comercial" description="Condiciones del tercero para ventas y compras.">
      <div className="space-y-4">
        {hasCliente ? (
          <div className="rounded-lg border border-border bg-background/70 p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Cliente</p>
            <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              <DetailRow label="Limite de credito" value={formatMoney(cliente?.limite_credito)} />
              <DetailRow label="Dias de credito" value={String(cliente?.dias_credito ?? 0)} />
              <DetailRow label="Categoria" value={cliente?.categoria_cliente || '-'} />
              <DetailRow label="Segmento" value={cliente?.segmento || '-'} />
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No tiene ficha de cliente asociada.</p>
        )}

        {hasProveedor ? (
          <div className="rounded-lg border border-border bg-background/70 p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Proveedor</p>
            <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              <DetailRow label="Giro" value={proveedor?.giro || '-'} />
              <DetailRow label="Vendedor contacto" value={proveedor?.vendedor_contacto || '-'} />
              <DetailRow label="Dias de credito" value={String(proveedor?.dias_credito ?? 0)} />
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No tiene ficha de proveedor asociada.</p>
        )}
      </div>
    </InfoCard>
  )
}

export default ContactoCommercialSection

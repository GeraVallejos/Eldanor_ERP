import { DetailRow, InfoCard } from '@/modules/contactos/components/ContactoDetailPrimitives'

function ContactoResumenSection({ contacto }) {
  return (
    <InfoCard title="Resumen maestro" description="Datos generales y de contacto del tercero dentro del ERP.">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <DetailRow label="Nombre" value={contacto.nombre || '-'} />
        <DetailRow label="Razon social" value={contacto.razon_social || '-'} />
        <DetailRow label="RUT" value={contacto.rut || '-'} />
        <DetailRow label="Tipo" value={contacto.tipo || '-'} />
        <DetailRow label="Email" value={contacto.email || '-'} />
        <DetailRow label="Telefono" value={contacto.telefono || contacto.celular || '-'} />
        <DetailRow label="Celular" value={contacto.celular || '-'} />
        <DetailRow label="Estado" value={contacto.activo ? 'Activo' : 'Inactivo'} />
      </div>

      <div className="mt-4 rounded-lg border border-dashed border-border px-4 py-3">
        <p className="text-xs uppercase tracking-wide text-muted-foreground">Notas</p>
        <p className="mt-2 text-sm text-foreground">{contacto.notas || 'Sin notas registradas.'}</p>
      </div>
    </InfoCard>
  )
}

export default ContactoResumenSection

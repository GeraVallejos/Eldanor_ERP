import { Link } from 'react-router-dom'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { formatDateTimeChile } from '@/lib/dateTimeFormat'
import { cn } from '@/lib/utils'
import {
  InfoCard,
  SectionTabButton,
  SeverityBadge,
} from '@/modules/contactos/components/ContactoDetailPrimitives'

const AUDIT_EVENT_LABELS = {
  CONTACTO_CREADO: 'Contacto creado',
  CONTACTO_ACTUALIZADO: 'Contacto actualizado',
  CONTACTO_ELIMINADO: 'Contacto eliminado',
  CLIENTE_CREADO: 'Cliente creado',
  CLIENTE_ACTUALIZADO: 'Cliente actualizado',
  CLIENTE_ELIMINADO: 'Cliente eliminado',
  PROVEEDOR_CREADO: 'Proveedor creado',
  PROVEEDOR_ACTUALIZADO: 'Proveedor actualizado',
  PROVEEDOR_ELIMINADO: 'Proveedor eliminado',
  DIRECCION_CREADA: 'Direccion creada',
  DIRECCION_ACTUALIZADA: 'Direccion actualizada',
  DIRECCION_ELIMINADA: 'Direccion eliminada',
  CUENTA_BANCARIA_CREADA: 'Cuenta bancaria creada',
  CUENTA_BANCARIA_ACTUALIZADA: 'Cuenta bancaria actualizada',
  CUENTA_BANCARIA_ELIMINADA: 'Cuenta bancaria eliminada',
  CONTACTOS_BULK_IMPORT: 'Importacion masiva',
}

const AUDIT_ENTITY_LABELS = {
  CONTACTO: 'Contacto',
  CLIENTE: 'Cliente',
  PROVEEDOR: 'Proveedor',
  DIRECCION: 'Direccion',
  CUENTA_BANCARIA: 'Cuenta bancaria',
}

function getAuditDate(evento) {
  return evento?.occurred_at || evento?.creado_en || null
}

function ContactoAuditSection({
  auditFilters,
  auditFilter,
  auditRows,
  auditStatus,
  filteredAuditRows,
  onFilterChange,
}) {
  return (
    <InfoCard
      title="Trazabilidad"
      description="Ultimos eventos de auditoria asociados al tercero, sus fichas comerciales y relaciones operativas."
    >
      {auditStatus === 'loading' ? <p className="text-sm text-muted-foreground">Cargando historial...</p> : null}

      {auditStatus === 'failed' ? (
        <p className="text-sm text-muted-foreground">No fue posible cargar la trazabilidad en este momento.</p>
      ) : null}

      {auditStatus === 'succeeded' && auditRows.length === 0 ? (
        <p className="text-sm text-muted-foreground">Todavia no hay eventos visibles para este tercero.</p>
      ) : null}

      {auditRows.length > 0 ? (
        <div className="space-y-4">
          <div className="flex flex-col gap-3 rounded-lg border border-dashed border-border px-4 py-3">
            <div className="flex flex-wrap items-center gap-2">
              {Object.entries(auditFilters).map(([filterKey, filterConfig]) => (
                <SectionTabButton
                  key={filterKey}
                  active={auditFilter === filterKey}
                  label={filterConfig.label}
                  onClick={() => onFilterChange(filterKey)}
                />
              ))}
            </div>
            <p className="text-xs text-muted-foreground">
              Mostrando {filteredAuditRows.length} de {auditRows.length} eventos consolidados.
            </p>
          </div>

          {filteredAuditRows.length === 0 ? (
            <p className="text-sm text-muted-foreground">No hay eventos para el filtro seleccionado.</p>
          ) : null}

          {filteredAuditRows.map((evento) => (
            <div key={evento.id} className="rounded-lg border border-border bg-background/70 p-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-medium text-foreground">
                      {AUDIT_EVENT_LABELS[evento.event_type] || evento.event_type || 'Evento de auditoria'}
                    </p>
                    <SeverityBadge severity={evento.severity} />
                  </div>
                  <p className="mt-1 text-xs uppercase tracking-wide text-muted-foreground">
                    {AUDIT_ENTITY_LABELS[evento.entity_type] || evento.entity_type || 'Entidad'}
                  </p>
                  <p className="mt-2 text-sm text-muted-foreground">{evento.summary || 'Sin resumen adicional.'}</p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {formatDateTimeChile(getAuditDate(evento))} | {evento.creado_por_email || 'Sistema'}
                  </p>
                </div>
                <Link
                  to={`/auditoria/eventos/${evento.id}`}
                  className={cn(buttonVariants({ variant: 'outline', size: 'sm' }), 'shrink-0')}
                >
                  Ver evento
                </Link>
              </div>
            </div>
          ))}
        </div>
      ) : null}

      <div className="mt-4">
        <Link to="/auditoria/eventos" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
          Abrir auditoria central
        </Link>
      </div>
    </InfoCard>
  )
}

export default ContactoAuditSection

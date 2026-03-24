import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { normalizeApiError } from '@/api/errors'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { cn } from '@/lib/utils'
import ContactoAuditSection from '@/modules/contactos/components/ContactoAuditSection'
import ContactoCommercialSection from '@/modules/contactos/components/ContactoCommercialSection'
import ContactoCuentasSection from '@/modules/contactos/components/ContactoCuentasSection'
import ContactoDireccionesSection from '@/modules/contactos/components/ContactoDireccionesSection'
import {
  SectionTabButton,
} from '@/modules/contactos/components/ContactoDetailPrimitives'
import ContactoResumenSection from '@/modules/contactos/components/ContactoResumenSection'
import { contactosApi } from '@/modules/contactos/store/api'
import { useTerceroDetail } from '@/modules/contactos/store/hooks'
import { usePermissions } from '@/modules/shared/auth/usePermission'

const EMPTY_DIRECCION_FORM = {
  tipo: 'COMERCIAL',
  direccion: '',
  comuna: '',
  ciudad: '',
  region: '',
  pais: 'CHILE',
}

const EMPTY_CUENTA_FORM = {
  banco: '',
  tipo_cuenta: 'CORRIENTE',
  numero_cuenta: '',
  titular: '',
  rut_titular: '',
  activa: true,
}

const AUDIT_FILTERS = {
  all: {
    label: 'Todos',
    matches: () => true,
  },
  maestro: {
    label: 'Maestro',
    matches: (evento) => evento?.entity_type === 'CONTACTO',
  },
  comercial: {
    label: 'Comercial',
    matches: (evento) => ['CLIENTE', 'PROVEEDOR'].includes(evento?.entity_type),
  },
  operacion: {
    label: 'Operacion',
    matches: (evento) => evento?.entity_type === 'DIRECCION',
  },
  finanzas: {
    label: 'Finanzas',
    matches: (evento) => evento?.entity_type === 'CUENTA_BANCARIA',
  },
}

function buildDireccionForm(direccion) {
  return {
    tipo: direccion?.tipo || 'COMERCIAL',
    direccion: direccion?.direccion || '',
    comuna: direccion?.comuna || '',
    ciudad: direccion?.ciudad || '',
    region: direccion?.region || '',
    pais: direccion?.pais || 'CHILE',
  }
}

function buildCuentaForm(cuenta) {
  return {
    banco: cuenta?.banco || '',
    tipo_cuenta: cuenta?.tipo_cuenta || 'CORRIENTE',
    numero_cuenta: cuenta?.numero_cuenta || '',
    titular: cuenta?.titular || '',
    rut_titular: cuenta?.rut_titular || '',
    activa: Boolean(cuenta?.activa),
  }
}

function normalizeAuditRows(data) {
  if (Array.isArray(data)) {
    return data
  }

  if (Array.isArray(data?.results)) {
    return data.results
  }

  return []
}

function ContactoDetailPage() {
  const { id } = useParams()
  const permissions = usePermissions(['CONTACTOS.EDITAR', 'CONTACTOS.BORRAR', 'AUDITORIA.VER'])
  const { status, contacto, cliente, proveedor, direcciones, cuentasBancarias, reload } = useTerceroDetail(id)
  const canEdit = permissions['CONTACTOS.EDITAR']
  const canDelete = permissions['CONTACTOS.BORRAR']
  const canViewAudit = permissions['AUDITORIA.VER']
  const shownErrorRef = useRef(false)
  const [direccionForm, setDireccionForm] = useState(EMPTY_DIRECCION_FORM)
  const [cuentaForm, setCuentaForm] = useState(EMPTY_CUENTA_FORM)
  const [savingDireccion, setSavingDireccion] = useState(false)
  const [savingCuenta, setSavingCuenta] = useState(false)
  const [deletingDireccionId, setDeletingDireccionId] = useState(null)
  const [deletingCuentaId, setDeletingCuentaId] = useState(null)
  const [editingDireccionId, setEditingDireccionId] = useState(null)
  const [editingDireccionForm, setEditingDireccionForm] = useState(EMPTY_DIRECCION_FORM)
  const [editingCuentaId, setEditingCuentaId] = useState(null)
  const [editingCuentaForm, setEditingCuentaForm] = useState(EMPTY_CUENTA_FORM)
  const [updatingDireccion, setUpdatingDireccion] = useState(false)
  const [updatingCuenta, setUpdatingCuenta] = useState(false)
  const [direccionToDelete, setDireccionToDelete] = useState(null)
  const [cuentaToDelete, setCuentaToDelete] = useState(null)
  const [auditStatus, setAuditStatus] = useState('idle')
  const [auditRows, setAuditRows] = useState([])
  const [activeSection, setActiveSection] = useState('resumen')
  const [auditFilter, setAuditFilter] = useState('all')

  useEffect(() => {
    if (status !== 'failed' || shownErrorRef.current) {
      return
    }
    toast.error('No se pudo cargar la ficha del contacto.')
    shownErrorRef.current = true
  }, [status])

  useEffect(() => {
    shownErrorRef.current = false
    setActiveSection('resumen')
    setAuditFilter('all')
    setDireccionToDelete(null)
    setCuentaToDelete(null)
  }, [id])

  useEffect(() => {
    if (!canViewAudit || activeSection !== 'auditoria') {
      setAuditStatus('idle')
      return
    }

    if (status !== 'succeeded' || !contacto) {
      setAuditRows([])
      setAuditStatus('idle')
      return
    }

    let active = true

    const loadAuditTrail = async () => {
      setAuditStatus('loading')
      try {
        const data = await contactosApi.getTerceroAudit(contacto.id, { limit: 8 })

        if (!active) {
          return
        }

        setAuditRows(normalizeAuditRows(data))
        setAuditStatus('succeeded')
      } catch (error) {
        if (!active) {
          return
        }
        toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar la trazabilidad del tercero.' }))
        setAuditStatus('failed')
      }
    }

    void loadAuditTrail()

    return () => {
      active = false
    }
  }, [activeSection, canViewAudit, contacto?.id, status])

  const filteredAuditRows = useMemo(() => {
    const predicate = AUDIT_FILTERS[auditFilter]?.matches || AUDIT_FILTERS.all.matches
    return auditRows.filter((evento) => predicate(evento))
  }, [auditFilter, auditRows])

  if (status === 'loading') {
    return <p className="text-sm text-muted-foreground">Cargando ficha del tercero...</p>
  }

  if (status === 'failed') {
    return (
      <section className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-2xl font-semibold">Ficha de contacto</h2>
            <p className="text-sm text-muted-foreground">No fue posible recuperar el tercero solicitado.</p>
          </div>
          <Link to="/contactos/clientes" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
            Volver
          </Link>
        </div>
      </section>
    )
  }

  if (!contacto) {
    return null
  }

  const hasCliente = Boolean(cliente)
  const hasProveedor = Boolean(proveedor)
  const roleLabel = [
    hasCliente ? 'Cliente' : null,
    hasProveedor ? 'Proveedor' : null,
  ].filter(Boolean).join(' + ') || 'Contacto'

  const updateDireccionField = (field, value) => {
    setDireccionForm((prev) => ({ ...prev, [field]: value }))
  }

  const updateCuentaField = (field, value) => {
    setCuentaForm((prev) => ({ ...prev, [field]: value }))
  }

  const updateEditingDireccionField = (field, value) => {
    setEditingDireccionForm((prev) => ({ ...prev, [field]: value }))
  }

  const updateEditingCuentaField = (field, value) => {
    setEditingCuentaForm((prev) => ({ ...prev, [field]: value }))
  }

  const submitDireccion = async (event) => {
    event.preventDefault()
    setSavingDireccion(true)
    try {
      await contactosApi.createOne(contactosApi.endpoints.direcciones, {
        contacto: id,
        tipo: direccionForm.tipo,
        direccion: direccionForm.direccion,
        comuna: direccionForm.comuna,
        ciudad: direccionForm.ciudad,
        region: direccionForm.region || null,
        pais: direccionForm.pais || 'CHILE',
      })
      toast.success('Direccion registrada correctamente.')
      setDireccionForm(EMPTY_DIRECCION_FORM)
      await reload()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo guardar la direccion.' }))
    } finally {
      setSavingDireccion(false)
    }
  }

  const submitCuenta = async (event) => {
    event.preventDefault()
    setSavingCuenta(true)
    try {
      await contactosApi.createOne(contactosApi.endpoints.cuentasBancarias, {
        contacto: id,
        banco: cuentaForm.banco,
        tipo_cuenta: cuentaForm.tipo_cuenta,
        numero_cuenta: cuentaForm.numero_cuenta,
        titular: cuentaForm.titular,
        rut_titular: cuentaForm.rut_titular,
        activa: Boolean(cuentaForm.activa),
      })
      toast.success('Cuenta bancaria registrada correctamente.')
      setCuentaForm(EMPTY_CUENTA_FORM)
      await reload()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo guardar la cuenta bancaria.' }))
    } finally {
      setSavingCuenta(false)
    }
  }

  const requestDeleteDireccion = (direccionId) => {
    const selectedDireccion = direcciones.find((direccion) => direccion.id === direccionId)
    setDireccionToDelete(selectedDireccion || { id: direccionId })
  }

  const removeDireccion = async () => {
    if (!direccionToDelete?.id) {
      return
    }

    setDeletingDireccionId(direccionToDelete.id)
    try {
      await contactosApi.removeOne(contactosApi.endpoints.direcciones, direccionToDelete.id)
      toast.success('Direccion eliminada correctamente.')
      setDireccionToDelete(null)
      await reload()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo eliminar la direccion.' }))
    } finally {
      setDeletingDireccionId(null)
    }
  }

  const startDireccionEdit = (direccion) => {
    setEditingDireccionId(direccion.id)
    setEditingDireccionForm(buildDireccionForm(direccion))
  }

  const cancelDireccionEdit = () => {
    setEditingDireccionId(null)
    setEditingDireccionForm(EMPTY_DIRECCION_FORM)
  }

  const submitDireccionEdit = async (event) => {
    event.preventDefault()
    if (!editingDireccionId) {
      return
    }

    setUpdatingDireccion(true)
    try {
      await contactosApi.updateOne(contactosApi.endpoints.direcciones, editingDireccionId, {
        tipo: editingDireccionForm.tipo,
        direccion: editingDireccionForm.direccion,
        comuna: editingDireccionForm.comuna,
        ciudad: editingDireccionForm.ciudad,
        region: editingDireccionForm.region || null,
        pais: editingDireccionForm.pais || 'CHILE',
      })
      toast.success('Direccion actualizada correctamente.')
      cancelDireccionEdit()
      await reload()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo actualizar la direccion.' }))
    } finally {
      setUpdatingDireccion(false)
    }
  }

  const requestDeleteCuenta = (cuentaId) => {
    const selectedCuenta = cuentasBancarias.find((cuenta) => cuenta.id === cuentaId)
    setCuentaToDelete(selectedCuenta || { id: cuentaId })
  }

  const removeCuenta = async () => {
    if (!cuentaToDelete?.id) {
      return
    }

    setDeletingCuentaId(cuentaToDelete.id)
    try {
      await contactosApi.removeOne(contactosApi.endpoints.cuentasBancarias, cuentaToDelete.id)
      toast.success('Cuenta bancaria eliminada correctamente.')
      setCuentaToDelete(null)
      await reload()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo eliminar la cuenta bancaria.' }))
    } finally {
      setDeletingCuentaId(null)
    }
  }

  const startCuentaEdit = (cuenta) => {
    setEditingCuentaId(cuenta.id)
    setEditingCuentaForm(buildCuentaForm(cuenta))
  }

  const cancelCuentaEdit = () => {
    setEditingCuentaId(null)
    setEditingCuentaForm(EMPTY_CUENTA_FORM)
  }

  const submitCuentaEdit = async (event) => {
    event.preventDefault()
    if (!editingCuentaId) {
      return
    }

    setUpdatingCuenta(true)
    try {
      await contactosApi.updateOne(contactosApi.endpoints.cuentasBancarias, editingCuentaId, {
        banco: editingCuentaForm.banco,
        tipo_cuenta: editingCuentaForm.tipo_cuenta,
        numero_cuenta: editingCuentaForm.numero_cuenta,
        titular: editingCuentaForm.titular,
        rut_titular: editingCuentaForm.rut_titular,
        activa: Boolean(editingCuentaForm.activa),
      })
      toast.success('Cuenta bancaria actualizada correctamente.')
      cancelCuentaEdit()
      await reload()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo actualizar la cuenta bancaria.' }))
    } finally {
      setUpdatingCuenta(false)
    }
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Maestro de terceros</p>
          <h2 className="mt-1 text-3xl font-semibold">{contacto.nombre || 'Contacto sin nombre'}</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            {roleLabel} | {contacto.rut || 'Sin RUT'} | {contacto.activo ? 'Activo' : 'Inactivo'}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to={hasCliente ? '/contactos/clientes' : '/contactos/proveedores'} className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
            Volver al listado
          </Link>
          {canEdit && hasCliente && cliente?.id ? (
            <Link to={`/contactos/clientes/${cliente.id}/editar`} className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
              Editar cliente
            </Link>
          ) : null}
          {canEdit && hasProveedor && proveedor?.id ? (
            <Link to={`/contactos/proveedores/${proveedor.id}/editar`} className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
              Editar proveedor
            </Link>
          ) : null}
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <SectionTabButton active={activeSection === 'resumen'} label="Resumen" onClick={() => setActiveSection('resumen')} />
        <SectionTabButton active={activeSection === 'operacion'} label="Operacion" onClick={() => setActiveSection('operacion')} />
        <SectionTabButton active={activeSection === 'finanzas'} label="Finanzas" onClick={() => setActiveSection('finanzas')} />
        {canViewAudit ? (
          <SectionTabButton active={activeSection === 'auditoria'} label="Auditoria" onClick={() => setActiveSection('auditoria')} />
        ) : null}
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
        <div className={cn('space-y-4', activeSection !== 'finanzas' ? '' : 'lg:col-span-2')}>
          <div className={cn(activeSection === 'resumen' ? 'block' : 'hidden')}>
            <ContactoResumenSection contacto={contacto} />
          </div>

          <div className={cn(activeSection === 'operacion' ? 'block' : 'hidden')}>
            <ContactoDireccionesSection
              canDelete={canDelete}
              canEdit={canEdit}
              deletingDireccionId={deletingDireccionId}
              direccionForm={direccionForm}
              direcciones={direcciones}
              editingDireccionForm={editingDireccionForm}
              editingDireccionId={editingDireccionId}
              onCancelEdit={cancelDireccionEdit}
              onChangeCreateField={updateDireccionField}
              onChangeEditField={updateEditingDireccionField}
              onDelete={requestDeleteDireccion}
              onStartEdit={startDireccionEdit}
              onSubmitCreate={submitDireccion}
              onSubmitEdit={submitDireccionEdit}
              savingDireccion={savingDireccion}
              updatingDireccion={updatingDireccion}
            />
          </div>
        </div>

        <div className="space-y-4">
          <div className={cn(activeSection === 'resumen' ? 'block' : 'hidden')}>
            <ContactoCommercialSection cliente={cliente} proveedor={proveedor} />
          </div>

          <div className={cn(activeSection === 'finanzas' ? 'block' : 'hidden')}>
            <ContactoCuentasSection
              canDelete={canDelete}
              canEdit={canEdit}
              cuentasBancarias={cuentasBancarias}
              cuentaForm={cuentaForm}
              deletingCuentaId={deletingCuentaId}
              editingCuentaForm={editingCuentaForm}
              editingCuentaId={editingCuentaId}
              onCancelEdit={cancelCuentaEdit}
              onChangeCreateField={updateCuentaField}
              onChangeEditField={updateEditingCuentaField}
              onDelete={requestDeleteCuenta}
              onStartEdit={startCuentaEdit}
              onSubmitCreate={submitCuenta}
              onSubmitEdit={submitCuentaEdit}
              savingCuenta={savingCuenta}
              updatingCuenta={updatingCuenta}
            />
          </div>

          {canViewAudit ? (
            <div className={cn(activeSection === 'auditoria' ? 'block' : 'hidden')}>
              <ContactoAuditSection
                auditFilters={AUDIT_FILTERS}
                auditFilter={auditFilter}
                auditRows={auditRows}
                auditStatus={auditStatus}
                filteredAuditRows={filteredAuditRows}
                onFilterChange={setAuditFilter}
              />
            </div>
          ) : null}
        </div>
      </div>

      <ConfirmDialog
        open={Boolean(direccionToDelete)}
        title="Eliminar direccion"
        description="Se eliminara la direccion del tercero y se registrara su trazabilidad en auditoria."
        confirmLabel="Eliminar"
        loading={deletingDireccionId === direccionToDelete?.id}
        onCancel={() => {
          if (!deletingDireccionId) {
            setDireccionToDelete(null)
          }
        }}
        onConfirm={removeDireccion}
      />

      <ConfirmDialog
        open={Boolean(cuentaToDelete)}
        title="Eliminar cuenta bancaria"
        description="Se eliminara la cuenta bancaria del tercero y se registrara su trazabilidad en auditoria."
        confirmLabel="Eliminar"
        loading={deletingCuentaId === cuentaToDelete?.id}
        onCancel={() => {
          if (!deletingCuentaId) {
            setCuentaToDelete(null)
          }
        }}
        onConfirm={removeCuenta}
      />
    </section>
  )
}

export default ContactoDetailPage

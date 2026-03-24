import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import ApiContractError from '@/components/ui/ApiContractError'
import Button from '@/components/ui/Button'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { cn } from '@/lib/utils'
import ContactoBaseFields from '@/modules/contactos/components/ContactoBaseFields'
import { contactosApi } from '@/modules/contactos/store/api'
import { useUpdateTerceroAction } from '@/modules/contactos/store/mutations'

const EMPTY_FORM = {
  clienteId: null,
  contactoId: null,
  nombre: '',
  razon_social: '',
  rut: '',
  tipo: 'EMPRESA',
  email: '',
  telefono: '',
  celular: '',
  notas: '',
  limite_credito: 0,
  dias_credito: 0,
  categoria_cliente: '',
  segmento: '',
  activo: true,
}

function ClientesEditPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [pageStatus, setPageStatus] = useState('loading')
  const [form, setForm] = useState(EMPTY_FORM)
  const [submitError, setSubmitError] = useState(null)

  const updateField = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const { status, saveTercero } = useUpdateTerceroAction({
    kind: 'cliente',
    successMessage: 'Cliente actualizado correctamente.',
    errorMessage: 'No se pudo actualizar el cliente.',
    buildPayload: (currentForm, contactoId) => ({
      contacto: contactoId,
      limite_credito: Number(currentForm.limite_credito) || 0,
      dias_credito: Number(currentForm.dias_credito) || 0,
      categoria_cliente: currentForm.categoria_cliente || null,
      segmento: currentForm.segmento || null,
    }),
    onSuccess: async () => {
      navigate(`/contactos/terceros/${form.contactoId}`)
    },
  })

  useEffect(() => {
    let active = true

    const loadCliente = async () => {
      try {
        const cliente = await contactosApi.getClienteEditDetail(id)
        const contacto = cliente.contacto
        if (!active) {
          return
        }

        setForm({
          clienteId: cliente.id,
          contactoId: contacto.id,
          nombre: contacto.nombre || '',
          razon_social: contacto.razon_social || '',
          rut: contacto.rut || '',
          tipo: contacto.tipo || 'EMPRESA',
          email: contacto.email || '',
          telefono: contacto.telefono || '',
          celular: contacto.celular || '',
          notas: contacto.notas || '',
          limite_credito: Number(cliente.limite_credito ?? 0),
          dias_credito: Number(cliente.dias_credito ?? 0),
          categoria_cliente: cliente.categoria_cliente || '',
          segmento: cliente.segmento || '',
          activo: Boolean(contacto.activo ?? true),
        })
        setPageStatus('succeeded')
      } catch (_error) {
        if (!active) {
          return
        }
        toast.error('No se pudo cargar el cliente.')
        setPageStatus('failed')
      }
    }

    void loadCliente()

    return () => {
      active = false
    }
  }, [id])

  const onSubmit = async (event) => {
    event.preventDefault()
    setSubmitError(null)

    if (!form.nombre.trim()) {
      toast.error('El nombre es obligatorio.')
      return
    }
    if (!form.rut.trim()) {
      toast.error('El RUT es obligatorio.')
      return
    }
    if (!form.email.trim()) {
      toast.error('El email es obligatorio.')
      return
    }

    const result = await saveTercero({
      form,
      contactoId: form.contactoId,
      terceroId: form.clienteId,
    })

    if (!result.ok) {
      setSubmitError(result.contract)
    }
  }

  if (pageStatus === 'loading') {
    return <p className="text-sm text-muted-foreground">Cargando cliente...</p>
  }

  if (pageStatus === 'failed') {
    return (
      <section className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-2xl font-semibold">Editar cliente</h2>
            <p className="text-sm text-muted-foreground">No fue posible cargar el cliente solicitado.</p>
          </div>
          <Link to="/contactos/clientes" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
            Volver al listado
          </Link>
        </div>
      </section>
    )
  }

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold">Editar cliente</h2>
          <p className="text-sm text-muted-foreground">Actualiza la ficha maestra y las condiciones comerciales del cliente.</p>
        </div>
        <Link
          to={form.contactoId ? `/contactos/terceros/${form.contactoId}` : '/contactos/clientes'}
          className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}
        >
          Volver
        </Link>
      </div>

      <form className="rounded-md border border-border bg-card p-4" onSubmit={onSubmit}>
        <ApiContractError error={typeof submitError === 'object' ? submitError : null} title="No se pudo actualizar el cliente." />
        <div className="grid gap-3 md:grid-cols-2">
          <ContactoBaseFields form={form} updateField={updateField} />

          <label className="text-sm">
            Limite de credito
            <input
              type="number"
              min="0"
              step="1"
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={form.limite_credito}
              onChange={(event) => updateField('limite_credito', event.target.value)}
            />
          </label>

          <label className="text-sm">
            Dias de credito
            <input
              type="number"
              min="0"
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={form.dias_credito}
              onChange={(event) => updateField('dias_credito', event.target.value)}
            />
          </label>

          <label className="text-sm">
            Categoria de cliente
            <input
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={form.categoria_cliente}
              onChange={(event) => updateField('categoria_cliente', event.target.value)}
            />
          </label>

          <label className="text-sm">
            Segmento
            <input
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={form.segmento}
              onChange={(event) => updateField('segmento', event.target.value)}
            />
          </label>
        </div>

        <div className="mt-4">
          <Button type="submit" size="md" disabled={status === 'loading'}>
            {status === 'loading' ? 'Guardando...' : 'Guardar cambios'}
          </Button>
        </div>
      </form>
    </section>
  )
}

export default ClientesEditPage

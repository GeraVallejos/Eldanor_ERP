import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import Button from '@/components/ui/Button'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { cn } from '@/lib/utils'
import ContactoBaseFields from '@/modules/contactos/components/ContactoBaseFields'
import { useCreateTerceroAction } from '@/modules/contactos/store/mutations'

function ClientesCreatePage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
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
  })

  const updateField = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const { status, saveTercero } = useCreateTerceroAction({
    kind: 'cliente',
    successMessage: 'Cliente creado correctamente.',
    errorMessage: 'No se pudo crear el cliente.',
    buildPayload: (currentForm, contactoId) => ({
      contacto: contactoId,
      limite_credito: Number(currentForm.limite_credito) || 0,
      dias_credito: Number(currentForm.dias_credito) || 0,
      categoria_cliente: currentForm.categoria_cliente || null,
      segmento: currentForm.segmento || null,
    }),
    onSuccess: async () => {
      navigate('/contactos/clientes')
    },
  })

  const onSubmit = async (event) => {
    event.preventDefault()

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

    await saveTercero(form)
  }

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold">Nuevo cliente</h2>
          <p className="text-sm text-muted-foreground">Crea un cliente y su contacto asociado.</p>
        </div>
        <Link
          to="/contactos/clientes"
          className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}
        >
          Volver al listado
        </Link>
      </div>

      <form className="rounded-md border border-border bg-card p-4" onSubmit={onSubmit}>
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
            {status === 'loading' ? 'Guardando...' : 'Crear cliente'}
          </Button>
        </div>
      </form>
    </section>
  )
}

export default ClientesCreatePage

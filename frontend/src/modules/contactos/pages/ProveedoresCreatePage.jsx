import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import Button from '@/components/ui/Button'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { cn } from '@/lib/utils'
import ContactoBaseFields from '@/modules/contactos/components/ContactoBaseFields'
import { useCreateTerceroAction } from '@/modules/contactos/store/mutations'

function ProveedoresCreatePage() {
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
    giro: '',
    vendedor_contacto: '',
    dias_credito: 0,
    activo: true,
  })

  const updateField = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const { status, saveTercero } = useCreateTerceroAction({
    kind: 'proveedor',
    successMessage: 'Proveedor creado correctamente.',
    errorMessage: 'No se pudo crear el proveedor.',
    buildPayload: (currentForm, contactoId) => ({
      contacto: contactoId,
      giro: currentForm.giro || null,
      vendedor_contacto: currentForm.vendedor_contacto || null,
      dias_credito: Number(currentForm.dias_credito) || 0,
    }),
    onSuccess: async () => {
      navigate('/contactos/proveedores')
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
          <h2 className="text-2xl font-semibold">Nuevo proveedor</h2>
          <p className="text-sm text-muted-foreground">Crea un proveedor y su contacto asociado.</p>
        </div>
        <Link
          to="/contactos/proveedores"
          className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}
        >
          Volver al listado
        </Link>
      </div>

      <form className="rounded-md border border-border bg-card p-4" onSubmit={onSubmit}>
        <div className="grid gap-3 md:grid-cols-2">
          <ContactoBaseFields form={form} updateField={updateField} />

          <label className="text-sm">
            Giro
            <input
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={form.giro}
              onChange={(event) => updateField('giro', event.target.value)}
            />
          </label>

          <label className="text-sm">
            Contacto vendedor
            <input
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={form.vendedor_contacto}
              onChange={(event) => updateField('vendedor_contacto', event.target.value)}
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
        </div>

        <div className="mt-4">
          <Button type="submit" size="md" disabled={status === 'loading'}>
            {status === 'loading' ? 'Guardando...' : 'Crear proveedor'}
          </Button>
        </div>
      </form>
    </section>
  )
}

export default ProveedoresCreatePage

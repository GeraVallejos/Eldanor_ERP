import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { cn } from '@/lib/utils'

function normalizeListResponse(data) {
  if (Array.isArray(data)) {
    return data
  }

  if (Array.isArray(data?.results)) {
    return data.results
  }

  return []
}

function normalizeRut(value) {
  return String(value || '')
    .replace(/\./g, '')
    .replace(/-/g, '')
    .replace(/\s+/g, '')
    .toUpperCase()
}

function findExistingContacto(contactos, form) {
  const rut = normalizeRut(form.rut)
  if (!rut) {
    return null
  }

  return contactos.find((contacto) => normalizeRut(contacto?.rut) === rut) || null
}

function ClientesCreatePage() {
  const navigate = useNavigate()
  const [status, setStatus] = useState('idle')
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

    setStatus('loading')

    try {
      const { data: contactosData } = await api.get('/contactos/', {
        suppressGlobalErrorToast: true,
      })

      const contactos = normalizeListResponse(contactosData)
      const contactoExistente = findExistingContacto(contactos, form)

      let contactoId = contactoExistente?.id

      if (!contactoId) {
        const { data: contacto } = await api.post(
          '/contactos/',
          {
            nombre: form.nombre,
            razon_social: form.razon_social || null,
            rut: form.rut || null,
            tipo: form.tipo,
            email: form.email || null,
            telefono: form.telefono || null,
            celular: form.celular || null,
            notas: form.notas || null,
            activo: form.activo,
          },
          { suppressGlobalErrorToast: true },
        )

        contactoId = contacto.id
      } else {
        toast.info('Se reutilizo un contacto existente para crear el cliente.')
      }

      await api.post(
        '/clientes/',
        {
          contacto: contactoId,
          limite_credito: Number(form.limite_credito) || 0,
          dias_credito: Number(form.dias_credito) || 0,
          categoria_cliente: form.categoria_cliente || null,
          segmento: form.segmento || null,
          activo: form.activo,
        },
        { suppressGlobalErrorToast: true },
      )

      toast.success('Cliente creado correctamente.')
      navigate('/contactos/clientes')
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo crear el cliente.' }))
    } finally {
      setStatus('idle')
    }
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
          <label className="text-sm">
            Nombre
            <input
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={form.nombre}
              onChange={(event) => updateField('nombre', event.target.value)}
              required
            />
          </label>

          <label className="text-sm">
            Razon social
            <input
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={form.razon_social}
              onChange={(event) => updateField('razon_social', event.target.value)}
            />
          </label>

          <label className="text-sm">
            RUT
            <input
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={form.rut}
              onChange={(event) => updateField('rut', event.target.value)}
              required
            />
          </label>

          <label className="text-sm">
            Tipo
            <select
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={form.tipo}
              onChange={(event) => updateField('tipo', event.target.value)}
            >
              <option value="PERSONA">Persona</option>
              <option value="EMPRESA">Empresa</option>
            </select>
          </label>

          <label className="text-sm">
            Email
            <input
              type="email"
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={form.email}
              onChange={(event) => updateField('email', event.target.value)}
              required
            />
          </label>

          <label className="text-sm">
            Telefono
            <input
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={form.telefono}
              onChange={(event) => updateField('telefono', event.target.value)}
            />
          </label>

          <label className="text-sm">
            Celular
            <input
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={form.celular}
              onChange={(event) => updateField('celular', event.target.value)}
            />
          </label>

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

          <label className="text-sm md:col-span-2">
            Notas
            <textarea
              rows={3}
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={form.notas}
              onChange={(event) => updateField('notas', event.target.value)}
            />
          </label>

          <label className="flex items-center gap-2 text-sm md:col-span-2">
            <input
              type="checkbox"
              checked={form.activo}
              onChange={(event) => updateField('activo', event.target.checked)}
            />
            Activo
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

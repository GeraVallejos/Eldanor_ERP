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

function normalizeText(value) {
  return String(value || '').trim().toLowerCase()
}

function findExistingContacto(contactos, form) {
  const rut = normalizeRut(form.rut)
  if (rut) {
    const matchByRut = contactos.find((contacto) => normalizeRut(contacto?.rut) === rut)
    if (matchByRut) {
      return matchByRut
    }
  }

  const email = normalizeText(form.email)
  const nombre = normalizeText(form.nombre)

  if (email && nombre) {
    return (
      contactos.find(
        (contacto) =>
          normalizeText(contacto?.email) === email && normalizeText(contacto?.nombre) === nombre,
      ) || null
    )
  }

  return null
}

function ProveedoresCreatePage() {
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
    giro: '',
    vendedor_contacto: '',
    dias_credito: 0,
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
        toast.info('Se reutilizo un contacto existente para crear el proveedor.')
      }

      await api.post(
        '/proveedores/',
        {
          contacto: contactoId,
          giro: form.giro || null,
          vendedor_contacto: form.vendedor_contacto || null,
          dias_credito: Number(form.dias_credito) || 0,
          activo: form.activo,
        },
        { suppressGlobalErrorToast: true },
      )

      toast.success('Proveedor creado correctamente.')
      navigate('/contactos/proveedores')
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo crear el proveedor.' }))
    } finally {
      setStatus('idle')
    }
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
            {status === 'loading' ? 'Guardando...' : 'Crear proveedor'}
          </Button>
        </div>
      </form>
    </section>
  )
}

export default ProveedoresCreatePage

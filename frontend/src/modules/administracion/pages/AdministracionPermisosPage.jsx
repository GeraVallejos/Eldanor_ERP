import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import { usePermission } from '@/modules/shared/auth/usePermission'

function AdministracionPermisosPage() {
  const canManage = usePermission('ADMINISTRACION.GESTIONAR_PERMISOS')
  const [catalogo, setCatalogo] = useState({})
  const [miembros, setMiembros] = useState([])
  const [plantillas, setPlantillas] = useState([])
  const [selectedRelacion, setSelectedRelacion] = useState('')
  const [selectedPermisos, setSelectedPermisos] = useState([])
  const [selectedPlantilla, setSelectedPlantilla] = useState('')

  const loadData = async () => {
    try {
      const [{ data: catalogoData }, { data: miembrosData }, { data: plantillasData }] = await Promise.all([
        api.get('/permisos/catalogo/', { suppressGlobalErrorToast: true }),
        api.get('/permisos/miembros-empresa/', { suppressGlobalErrorToast: true }),
        api.get('/permisos/plantillas/', { suppressGlobalErrorToast: true }),
      ])
      setCatalogo(catalogoData || {})
      setMiembros(Array.isArray(miembrosData) ? miembrosData : [])
      setPlantillas(Array.isArray(plantillasData) ? plantillasData : [])
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar la administración de permisos.' }))
    }
  }

  useEffect(() => {
    if (canManage) {
      const id = setTimeout(() => { void loadData() }, 0)
      return () => clearTimeout(id)
    }
  }, [canManage])

  const opcionesPermisos = useMemo(() => {
    return Object.entries(catalogo).flatMap(([modulo, acciones]) => (
      Array.isArray(acciones) ? acciones.map((accion) => `${modulo}.${accion}`) : []
    ))
  }, [catalogo])

  const miembroSeleccionado = miembros.find((item) => String(item.relacion_id) === String(selectedRelacion))

  const togglePermiso = (permiso) => {
    setSelectedPermisos((prev) => (
      prev.includes(permiso) ? prev.filter((item) => item !== permiso) : [...prev, permiso]
    ))
  }

  const guardarPermisos = async () => {
    try {
      await api.post('/permisos/asignar/', {
        relacion_id: Number(selectedRelacion),
        permisos: selectedPermisos,
      }, { suppressGlobalErrorToast: true })
      toast.success('Permisos actualizados.')
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron guardar los permisos.' }))
    }
  }

  const aplicarPlantilla = async () => {
    try {
      await api.post('/permisos/plantillas/aplicar/', {
        relacion_id: Number(selectedRelacion),
        plantilla_codigo: selectedPlantilla,
      }, { suppressGlobalErrorToast: true })
      toast.success('Plantilla aplicada.')
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo aplicar la plantilla.' }))
    }
  }

  if (!canManage) {
    return <p className="text-sm text-destructive">No tiene permiso para gestionar permisos.</p>
  }

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold">Permisos y plantillas</h2>
        <p className="text-sm text-muted-foreground">Gestión operativa de accesos por usuario dentro de la empresa activa.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-[320px_minmax(0,1fr)]">
        <div className="space-y-3 rounded-md border border-border bg-card p-4">
          <label className="text-sm">
            Miembro empresa
            <select
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={selectedRelacion}
              onChange={(event) => {
                const relacionId = event.target.value
                const miembro = miembros.find((item) => String(item.relacion_id) === String(relacionId))
                setSelectedRelacion(relacionId)
                setSelectedPermisos(miembro?.permisos_personalizados || [])
              }}
            >
              <option value="">Seleccione</option>
              {miembros.map((miembro) => (
                <option key={miembro.relacion_id} value={miembro.relacion_id}>
                  {miembro.nombre} ({miembro.rol})
                </option>
              ))}
            </select>
          </label>

          <label className="text-sm">
            Plantilla
            <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={selectedPlantilla} onChange={(event) => setSelectedPlantilla(event.target.value)}>
              <option value="">Seleccione</option>
              {plantillas.map((plantilla) => (
                <option key={plantilla.codigo} value={plantilla.codigo}>
                  {plantilla.nombre}
                </option>
              ))}
            </select>
          </label>

          <div className="flex gap-2">
            <Button type="button" disabled={!selectedRelacion || !selectedPlantilla} onClick={aplicarPlantilla}>Aplicar plantilla</Button>
            <Button type="button" variant="outline" disabled={!selectedRelacion} onClick={guardarPermisos}>Guardar permisos</Button>
          </div>
        </div>

        <div className="rounded-md border border-border bg-card p-4">
          {!selectedRelacion ? (
            <p className="text-sm text-muted-foreground">Seleccione un miembro para editar permisos.</p>
          ) : (
            <div className="space-y-4">
              <div>
                <p className="text-sm font-medium">{miembroSeleccionado?.nombre}</p>
                <p className="text-xs text-muted-foreground">{miembroSeleccionado?.email}</p>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                {opcionesPermisos.map((permiso) => (
                  <label key={permiso} className="inline-flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={selectedPermisos.includes(permiso)} onChange={() => togglePermiso(permiso)} />
                    {permiso}
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

export default AdministracionPermisosPage

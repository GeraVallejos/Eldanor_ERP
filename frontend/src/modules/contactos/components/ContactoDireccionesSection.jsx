import Button from '@/components/ui/Button'
import { InfoCard } from '@/modules/contactos/components/ContactoDetailPrimitives'

function ContactoDireccionesSection({
  canDelete,
  canEdit,
  deletingDireccionId,
  direccionForm,
  direcciones,
  editingDireccionForm,
  editingDireccionId,
  onCancelEdit,
  onChangeCreateField,
  onChangeEditField,
  onDelete,
  onStartEdit,
  onSubmitCreate,
  onSubmitEdit,
  savingDireccion,
  updatingDireccion,
}) {
  return (
    <InfoCard title="Direcciones" description="Direcciones operativas y tributarias asociadas al tercero.">
      {direcciones.length === 0 ? (
        <p className="text-sm text-muted-foreground">No hay direcciones registradas.</p>
      ) : (
        <div className="grid gap-3">
          {direcciones.map((direccion) => (
            <div key={direccion.id} className="rounded-lg border border-border bg-background/70 p-4">
              {editingDireccionId === direccion.id ? (
                <form className="grid gap-3 md:grid-cols-2" onSubmit={onSubmitEdit}>
                  <label className="text-sm">
                    Tipo de direccion
                    <select
                      className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                      value={editingDireccionForm.tipo}
                      onChange={(event) => onChangeEditField('tipo', event.target.value)}
                    >
                      <option value="FACTURACION">Facturacion</option>
                      <option value="DESPACHO">Despacho</option>
                      <option value="COMERCIAL">Comercial</option>
                      <option value="PERSONAL">Personal</option>
                    </select>
                  </label>
                  <label className="text-sm md:col-span-2">
                    Direccion editada
                    <input
                      className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                      value={editingDireccionForm.direccion}
                      onChange={(event) => onChangeEditField('direccion', event.target.value)}
                      required
                    />
                  </label>
                  <label className="text-sm">
                    Comuna editada
                    <input
                      className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                      value={editingDireccionForm.comuna}
                      onChange={(event) => onChangeEditField('comuna', event.target.value)}
                      required
                    />
                  </label>
                  <label className="text-sm">
                    Ciudad editada
                    <input
                      className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                      value={editingDireccionForm.ciudad}
                      onChange={(event) => onChangeEditField('ciudad', event.target.value)}
                      required
                    />
                  </label>
                  <label className="text-sm">
                    Region editada
                    <input
                      className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                      value={editingDireccionForm.region}
                      onChange={(event) => onChangeEditField('region', event.target.value)}
                    />
                  </label>
                  <label className="text-sm">
                    Pais editado
                    <input
                      className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                      value={editingDireccionForm.pais}
                      onChange={(event) => onChangeEditField('pais', event.target.value)}
                    />
                  </label>
                  <div className="md:col-span-2 flex flex-wrap gap-2">
                    <Button type="submit" disabled={updatingDireccion}>
                      {updatingDireccion ? 'Guardando cambios...' : 'Guardar direccion'}
                    </Button>
                    <Button type="button" variant="outline" onClick={onCancelEdit} disabled={updatingDireccion}>
                      Cancelar
                    </Button>
                  </div>
                </form>
              ) : (
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-foreground">{direccion.tipo || 'Direccion sin tipo'}</p>
                    <p className="mt-1 text-sm text-muted-foreground">{direccion.direccion || '-'}</p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {[direccion.comuna, direccion.ciudad, direccion.region].filter(Boolean).join(' | ') || '-'}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">{direccion.pais || '-'}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {canEdit ? (
                      <Button type="button" size="sm" variant="outline" onClick={() => onStartEdit(direccion)}>
                        Editar
                      </Button>
                    ) : null}
                    {canDelete ? (
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        disabled={deletingDireccionId === direccion.id}
                        className="border-destructive/40 text-destructive hover:bg-destructive/10"
                        onClick={() => onDelete(direccion.id)}
                      >
                        {deletingDireccionId === direccion.id ? 'Eliminando...' : 'Eliminar'}
                      </Button>
                    ) : null}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {canEdit ? (
        <form className="mt-4 grid gap-3 rounded-lg border border-dashed border-border p-4 md:grid-cols-2" onSubmit={onSubmitCreate}>
          <label className="text-sm">
            Tipo
            <select
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={direccionForm.tipo}
              onChange={(event) => onChangeCreateField('tipo', event.target.value)}
            >
              <option value="FACTURACION">Facturacion</option>
              <option value="DESPACHO">Despacho</option>
              <option value="COMERCIAL">Comercial</option>
              <option value="PERSONAL">Personal</option>
            </select>
          </label>
          <label className="text-sm md:col-span-2">
            Direccion
            <input
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={direccionForm.direccion}
              onChange={(event) => onChangeCreateField('direccion', event.target.value)}
              required
            />
          </label>
          <label className="text-sm">
            Comuna
            <input
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={direccionForm.comuna}
              onChange={(event) => onChangeCreateField('comuna', event.target.value)}
              required
            />
          </label>
          <label className="text-sm">
            Ciudad
            <input
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={direccionForm.ciudad}
              onChange={(event) => onChangeCreateField('ciudad', event.target.value)}
              required
            />
          </label>
          <label className="text-sm">
            Region
            <input
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={direccionForm.region}
              onChange={(event) => onChangeCreateField('region', event.target.value)}
            />
          </label>
          <label className="text-sm">
            Pais
            <input
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={direccionForm.pais}
              onChange={(event) => onChangeCreateField('pais', event.target.value)}
            />
          </label>
          <div className="md:col-span-2">
            <Button type="submit" disabled={savingDireccion}>
              {savingDireccion ? 'Guardando direccion...' : 'Agregar direccion'}
            </Button>
          </div>
        </form>
      ) : null}
    </InfoCard>
  )
}

export default ContactoDireccionesSection

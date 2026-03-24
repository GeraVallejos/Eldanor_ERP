import Button from '@/components/ui/Button'
import { InfoCard } from '@/modules/contactos/components/ContactoDetailPrimitives'

function ContactoCuentasSection({
  canDelete,
  canEdit,
  cuentasBancarias,
  cuentaForm,
  deletingCuentaId,
  editingCuentaForm,
  editingCuentaId,
  onCancelEdit,
  onChangeCreateField,
  onChangeEditField,
  onDelete,
  onStartEdit,
  onSubmitCreate,
  onSubmitEdit,
  savingCuenta,
  updatingCuenta,
}) {
  return (
    <InfoCard title="Cuentas bancarias" description="Medios de pago registrados para operaciones con este tercero.">
      {cuentasBancarias.length === 0 ? (
        <p className="text-sm text-muted-foreground">No hay cuentas bancarias registradas.</p>
      ) : (
        <div className="space-y-3">
          {cuentasBancarias.map((cuenta) => (
            <div key={cuenta.id} className="rounded-lg border border-border bg-background/70 p-4">
              {editingCuentaId === cuenta.id ? (
                <form className="grid gap-3 md:grid-cols-2" onSubmit={onSubmitEdit}>
                  <label className="text-sm">
                    Banco editado
                    <input
                      className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                      value={editingCuentaForm.banco}
                      onChange={(event) => onChangeEditField('banco', event.target.value)}
                      required
                    />
                  </label>
                  <label className="text-sm">
                    Tipo de cuenta editado
                    <select
                      className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                      value={editingCuentaForm.tipo_cuenta}
                      onChange={(event) => onChangeEditField('tipo_cuenta', event.target.value)}
                    >
                      <option value="CORRIENTE">Corriente</option>
                      <option value="VISTA">Vista</option>
                      <option value="AHORRO">Ahorro</option>
                    </select>
                  </label>
                  <label className="text-sm">
                    Numero de cuenta editado
                    <input
                      className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                      value={editingCuentaForm.numero_cuenta}
                      onChange={(event) => onChangeEditField('numero_cuenta', event.target.value)}
                      required
                    />
                  </label>
                  <label className="text-sm">
                    Titular editado
                    <input
                      className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                      value={editingCuentaForm.titular}
                      onChange={(event) => onChangeEditField('titular', event.target.value)}
                      required
                    />
                  </label>
                  <label className="text-sm">
                    RUT titular editado
                    <input
                      className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                      value={editingCuentaForm.rut_titular}
                      onChange={(event) => onChangeEditField('rut_titular', event.target.value)}
                      required
                    />
                  </label>
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={editingCuentaForm.activa}
                      onChange={(event) => onChangeEditField('activa', event.target.checked)}
                    />
                    Cuenta activa
                  </label>
                  <div className="md:col-span-2 flex flex-wrap gap-2">
                    <Button type="submit" disabled={updatingCuenta}>
                      {updatingCuenta ? 'Guardando cambios...' : 'Guardar cuenta'}
                    </Button>
                    <Button type="button" variant="outline" onClick={onCancelEdit} disabled={updatingCuenta}>
                      Cancelar
                    </Button>
                  </div>
                </form>
              ) : (
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-foreground">{cuenta.banco || 'Banco sin nombre'}</p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {cuenta.tipo_cuenta || '-'} | {cuenta.numero_cuenta || '-'}
                    </p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {cuenta.titular || '-'} | {cuenta.rut_titular || '-'}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">{cuenta.activa ? 'Activa' : 'Inactiva'}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {canEdit ? (
                      <Button type="button" size="sm" variant="outline" onClick={() => onStartEdit(cuenta)}>
                        Editar
                      </Button>
                    ) : null}
                    {canDelete ? (
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        disabled={deletingCuentaId === cuenta.id}
                        className="border-destructive/40 text-destructive hover:bg-destructive/10"
                        onClick={() => onDelete(cuenta.id)}
                      >
                        {deletingCuentaId === cuenta.id ? 'Eliminando...' : 'Eliminar'}
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
            Banco
            <input
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={cuentaForm.banco}
              onChange={(event) => onChangeCreateField('banco', event.target.value)}
              required
            />
          </label>
          <label className="text-sm">
            Tipo de cuenta
            <select
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={cuentaForm.tipo_cuenta}
              onChange={(event) => onChangeCreateField('tipo_cuenta', event.target.value)}
            >
              <option value="CORRIENTE">Corriente</option>
              <option value="VISTA">Vista</option>
              <option value="AHORRO">Ahorro</option>
            </select>
          </label>
          <label className="text-sm">
            Numero de cuenta
            <input
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={cuentaForm.numero_cuenta}
              onChange={(event) => onChangeCreateField('numero_cuenta', event.target.value)}
              required
            />
          </label>
          <label className="text-sm">
            Titular
            <input
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={cuentaForm.titular}
              onChange={(event) => onChangeCreateField('titular', event.target.value)}
              required
            />
          </label>
          <label className="text-sm">
            RUT titular
            <input
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={cuentaForm.rut_titular}
              onChange={(event) => onChangeCreateField('rut_titular', event.target.value)}
              required
            />
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={cuentaForm.activa}
              onChange={(event) => onChangeCreateField('activa', event.target.checked)}
            />
            Activa
          </label>
          <div className="md:col-span-2">
            <Button type="submit" disabled={savingCuenta}>
              {savingCuenta ? 'Guardando cuenta...' : 'Agregar cuenta bancaria'}
            </Button>
          </div>
        </form>
      ) : null}
    </InfoCard>
  )
}

export default ContactoCuentasSection

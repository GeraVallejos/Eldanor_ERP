function ContactoBaseFields({ form, updateField }) {
  return (
    <>
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
    </>
  )
}

export default ContactoBaseFields

function ErrorContratoVenta({ error }) {
  const detail = error?.response?.data?.detail
  const errorCode = error?.response?.data?.error_code

  if (!detail && !errorCode) {
    return null
  }

  return (
    <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3">
      <p className="text-sm font-medium text-destructive">No se pudo completar la accion.</p>
      {typeof detail === 'string' ? (
        <p className="mt-1 text-sm text-destructive/90">{detail}</p>
      ) : null}
      {errorCode ? (
        <p className="mt-1 text-xs uppercase tracking-wide text-destructive/80">Codigo: {errorCode}</p>
      ) : null}
    </div>
  )
}

export default ErrorContratoVenta

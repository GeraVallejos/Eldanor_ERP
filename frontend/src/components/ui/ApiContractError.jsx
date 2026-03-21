function renderDetail(detail) {
  if (!detail) {
    return null
  }

  if (typeof detail === 'string') {
    return <p className="mt-1 text-sm text-destructive/90">{detail}</p>
  }

  if (Array.isArray(detail)) {
    return (
      <div className="mt-2 space-y-1 text-sm text-destructive/90">
        {detail.map((item, index) => (
          <p key={`${index}-${String(item)}`}>{String(item)}</p>
        ))}
      </div>
    )
  }

  if (typeof detail === 'object') {
    return (
      <div className="mt-2 space-y-1 text-sm text-destructive/90">
        {Object.entries(detail).map(([field, value]) => (
          <p key={field}>
            <span className="font-medium">{field}:</span>{' '}
            {Array.isArray(value) ? value.join(' ') : String(value)}
          </p>
        ))}
      </div>
    )
  }

  return <p className="mt-1 text-sm text-destructive/90">{String(detail)}</p>
}

function ApiContractError({ error, title = 'No se pudo completar la accion.' }) {
  if (!error?.message && !error?.detail && !error?.errorCode) {
    return null
  }

  return (
    <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3">
      <p className="text-sm font-medium text-destructive">{title}</p>
      {error.message ? <p className="mt-1 text-sm text-destructive/90">{error.message}</p> : null}
      {renderDetail(error.detail)}
      {error.errorCode ? (
        <p className="mt-2 text-xs uppercase tracking-wide text-destructive/80">
          Codigo: {error.errorCode}
        </p>
      ) : null}
    </div>
  )
}

export default ApiContractError

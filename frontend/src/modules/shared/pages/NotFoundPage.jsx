import { Link } from 'react-router-dom'

function NotFoundPage() {
  return (
    <section className="mx-auto max-w-md rounded-lg border border-border bg-card p-6 text-center shadow-sm">
      <h2 className="text-2xl font-semibold">404</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        La ruta solicitada no existe.
      </p>
      <Link
        to="/productos"
        className="mt-4 inline-block rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
      >
        Ir al inicio
      </Link>
    </section>
  )
}

export default NotFoundPage

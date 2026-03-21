import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import ApiContractError from '@/components/ui/ApiContractError'

describe('ApiContractError', () => {
  it('renderiza detail estructurado y error code', () => {
    render(
      <ApiContractError
        title="No se pudo guardar."
        error={{
          message: 'Revise los datos.',
          detail: { sku: ['Ya existe un producto con este SKU.'] },
          errorCode: 'CONFLICT',
        }}
      />,
    )

    expect(screen.getByText('No se pudo guardar.')).toBeInTheDocument()
    expect(screen.getByText('Revise los datos.')).toBeInTheDocument()
    expect(screen.getByText(/sku:/i)).toBeInTheDocument()
    expect(screen.getByText(/Codigo: CONFLICT/i)).toBeInTheDocument()
  })
})

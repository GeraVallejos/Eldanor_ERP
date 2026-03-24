import { fireEvent, render, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import BulkImportButton from '@/components/ui/BulkImportButton'

const postMock = vi.fn()
const getMock = vi.fn()
const successMock = vi.fn()
const errorMock = vi.fn()
const warningMock = vi.fn()
const infoMock = vi.fn()
const downloadErrorsMock = vi.fn()

vi.mock('@/api/client', () => ({
  api: {
    post: (...args) => postMock(...args),
    get: (...args) => getMock(...args),
  },
}))

vi.mock('sonner', () => ({
  toast: {
    success: (...args) => successMock(...args),
    error: (...args) => errorMock(...args),
    warning: (...args) => warningMock(...args),
    info: (...args) => infoMock(...args),
  },
}))

vi.mock('@/modules/shared/exports/downloadBulkImportErrorsFile', () => ({
  downloadBulkImportErrorsFile: (...args) => downloadErrorsMock(...args),
}))

describe('BulkImportButton', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('descarga reporte de errores cuando la carga masiva devuelve filas fallidas', async () => {
    postMock.mockResolvedValueOnce({
      data: {
        created: 1,
        updated: 0,
        successful_rows: 1,
        errors: [
          {
            line: 4,
            detail: 'SKU duplicado.',
            sku: 'SKU-001',
          },
        ],
      },
    })

    const { container } = render(<BulkImportButton endpoint="/productos/bulk_import/" templateEndpoint="/productos/bulk_template/" />)
    const input = container.querySelector('input[type="file"]')
    const file = new File(['nombre,sku\nProducto,SKU-001'], 'productos.csv', { type: 'text/csv' })

    fireEvent.change(input, { target: { files: [file] } })

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledTimes(1)
    })

    expect(successMock).toHaveBeenCalled()
    expect(warningMock).toHaveBeenCalledWith('Primera fila con error (linea 4): SKU duplicado.')
    expect(downloadErrorsMock).toHaveBeenCalledWith({
      errors: [
        {
          line: 4,
          detail: 'SKU duplicado.',
          sku: 'SKU-001',
        },
      ],
      endpoint: '/productos/bulk_import/',
    })
  })

  it('previsualiza antes de importar cuando el modo preview esta habilitado', async () => {
    postMock
      .mockResolvedValueOnce({
        data: {
          dry_run: true,
          created: 2,
          updated: 1,
          successful_rows: 3,
          warnings: [
            {
              code: 'PRECIO_CERO',
              line: 3,
              sku: 'SKU-000',
              detail: 'El producto DEMO se importara con precio 0 en la lista.',
            },
          ],
          errors: [
            {
              line: 4,
              detail: 'SKU no existe.',
              sku: 'SKU-404',
            },
            {
              line: 6,
              detail: 'Precio invalido.',
              sku: 'SKU-ERR-2',
            },
          ],
        },
      })
      .mockResolvedValueOnce({
        data: {
          created: 2,
          updated: 1,
          successful_rows: 3,
          warnings: [
            {
              code: 'PRECIO_CERO',
              line: 3,
              sku: 'SKU-000',
              detail: 'El producto DEMO se importara con precio 0 en la lista.',
            },
          ],
          errors: [],
        },
      })

    const { container, getByText } = render(
      <BulkImportButton
        endpoint="/listas-precio/1/bulk_import/"
        templateEndpoint="/listas-precio/1/bulk_template/"
        previewBeforeImport
      />,
    )
    const input = container.querySelector('input[type="file"]')
    const file = new File(['sku,precio\nSKU-001,1200'], 'lista.csv', { type: 'text/csv' })

    fireEvent.change(input, { target: { files: [file] } })

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledTimes(1)
    })

    expect(postMock.mock.calls[0][1].get('dry_run')).toBe('true')
    expect(getByText('Confirmar importacion')).toBeInTheDocument()
    expect(getByText(/Se crearan 2 registros y se actualizaran 1/i)).toBeInTheDocument()
    expect(getByText(/Advertencias detectadas: 1 fila\(s\) validas requieren atencion/i)).toBeInTheDocument()
    expect(getByText(/Fila 3: El producto DEMO se importara con precio 0 en la lista/i)).toBeInTheDocument()
    expect(getByText(/2 filas quedaran con error/i)).toBeInTheDocument()
    expect(getByText(/Fila 4: SKU no existe/i)).toBeInTheDocument()
    expect(getByText(/Fila 6: Precio invalido/i)).toBeInTheDocument()

    fireEvent.click(getByText('Importar archivo'))

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledTimes(2)
    })

    expect(postMock.mock.calls[1][1].get('dry_run')).toBeNull()
    expect(successMock).toHaveBeenCalled()
    expect(warningMock).toHaveBeenCalledWith(
      'Advertencia de carga (linea 3): El producto DEMO se importara con precio 0 en la lista.',
    )
  })

  it('muestra el dialogo de preview aunque todas las filas tengan error', async () => {
    postMock.mockResolvedValueOnce({
      data: {
        dry_run: true,
        created: 0,
        updated: 0,
        successful_rows: 0,
        warnings: [],
        errors: [
          {
            line: 2,
            detail: 'SKU no existe.',
            sku: 'SKU-404',
          },
          {
            line: 3,
            detail: 'Precio invalido.',
            sku: 'SKU-500',
          },
        ],
      },
    })

    const { container, getByText, queryByText } = render(
      <BulkImportButton
        endpoint="/clientes/bulk_import/"
        templateEndpoint="/clientes/bulk_template/"
        previewBeforeImport
      />,
    )
    const input = container.querySelector('input[type="file"]')
    const file = new File(['nombre\n'], 'clientes.csv', { type: 'text/csv' })

    fireEvent.change(input, { target: { files: [file] } })

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledTimes(1)
    })

    expect(getByText('Confirmar importacion')).toBeInTheDocument()
    expect(getByText(/No se detectaron filas validas para importar/i)).toBeInTheDocument()
    expect(getByText(/Fila 2: SKU no existe/i)).toBeInTheDocument()
    expect(getByText(/Fila 3: Precio invalido/i)).toBeInTheDocument()
    expect(queryByText('Importar archivo')).not.toBeInTheDocument()
    expect(errorMock).not.toHaveBeenCalled()
    expect(warningMock).not.toHaveBeenCalled()
    expect(downloadErrorsMock).not.toHaveBeenCalled()
  })
})

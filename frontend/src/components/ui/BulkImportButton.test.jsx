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
})

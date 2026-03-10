import { render } from '@testing-library/react'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'
import { createTestStore } from '@/test/utils/createTestStore'

export function renderWithProviders(ui, options = {}) {
  const {
    preloadedState,
    store = createTestStore(preloadedState),
    initialEntries = ['/'],
  } = options

  function Wrapper({ children }) {
    return (
      <Provider store={store}>
        <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
      </Provider>
    )
  }

  return {
    store,
    ...render(ui, { wrapper: Wrapper }),
  }
}

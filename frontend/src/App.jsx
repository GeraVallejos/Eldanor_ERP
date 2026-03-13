import { RouterProvider } from 'react-router-dom'
import router from '@/config/router'
import GlobalLoadingBar from '@/components/ui/GlobalLoadingBar'

function App() {
  return (
    <>
      <GlobalLoadingBar />
      <RouterProvider router={router} />
    </>
  )
}

export default App

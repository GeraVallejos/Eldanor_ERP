import { useSelector } from 'react-redux'
import { selectIsGlobalLoading } from '@/modules/shared/ui/uiSlice'

function GlobalLoadingBar() {
  const isLoading = useSelector(selectIsGlobalLoading)

  if (!isLoading) {
    return null
  }

  return (
    <div className="pointer-events-none fixed inset-x-0 top-0 z-70">
      <div className="h-0.5 w-full overflow-hidden bg-primary/20">
        <div className="h-full w-1/3 animate-[loading-slide_1.2s_ease-in-out_infinite] bg-primary" />
      </div>
    </div>
  )
}

export default GlobalLoadingBar

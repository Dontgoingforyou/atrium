import { ErrorBoundary } from './components/common/ErrorBoundary'
import { AppRoutes } from './routes'

export default function App() {
  return (
    <ErrorBoundary>
      <AppRoutes />
    </ErrorBoundary>
  )
}

import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom'
import { Dashboard } from './Dashboard'
import { Loading } from './components'

const router = createBrowserRouter([
  { path: '/', element: <Dashboard /> },
  {
    path: '/documents/:id',
    lazy: async () => ({ Component: (await import('./DocumentEditor')).DocumentRoute }),
    hydrateFallbackElement: <main className="editor-main"><Loading label="Loading editor…" /></main>,
  },
  { path: '*', element: <Navigate to="/" replace /> },
])

export default function App() {
  return <RouterProvider router={router} />
}

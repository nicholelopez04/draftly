import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Dashboard } from './Dashboard'
import { Loading } from './components'
import { DemoUserContext, migrateDemoUser, persistDemoUser, restoreDemoUser } from './demoUser'

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
  const [userId, setUserId] = useState(restoreDemoUser)
  useEffect(migrateDemoUser, [])

  function switchUser(id: number) {
    persistDemoUser(id)
    setUserId(id)
  }
  return (
    <DemoUserContext.Provider value={{ userId, switchUser }}>
      <RouterProvider router={router} />
    </DemoUserContext.Provider>
  )
}

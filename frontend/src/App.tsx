import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom'
import { useState } from 'react'
import { Dashboard } from './Dashboard'
import { Loading } from './components'
import { DemoUserContext } from './demoUser'

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
  const [userId, setUserId] = useState(() => sessionStorage.getItem('draftly-demo-user') === '2' ? 2 : 1)
  function switchUser(id: number) {
    sessionStorage.setItem('draftly-demo-user', String(id))
    setUserId(id)
  }
  return (
    <DemoUserContext.Provider value={{ userId, switchUser }}>
      <RouterProvider router={router} />
    </DemoUserContext.Provider>
  )
}

import { createContext, useContext } from 'react'

const storageKey = 'draftly-demo-user'

function readUser(storage: 'localStorage' | 'sessionStorage') {
  try {
    const value = window[storage].getItem(storageKey)
    return value === '1' ? 1 : value === '2' ? 2 : null
  } catch {
    return null
  }
}

export function restoreDemoUser() {
  return readUser('localStorage') ?? readUser('sessionStorage') ?? 1
}

export function persistDemoUser(userId: number) {
  try {
    window.localStorage.setItem(storageKey, String(userId))
  } catch {
    // The active tab can still switch users if the browser blocks storage.
  }
}

export function migrateDemoUser() {
  if (readUser('localStorage') !== null) return
  const previousUser = readUser('sessionStorage')
  if (previousUser !== null) persistDemoUser(previousUser)
}

export const DemoUserContext = createContext({
  userId: 1,
  switchUser: (_id: number) => {},
})

export const useDemoUser = () => useContext(DemoUserContext)

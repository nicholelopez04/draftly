import { createContext, useContext } from 'react'

export const DemoUserContext = createContext({
  userId: 1,
  switchUser: (_id: number) => {},
})

export const useDemoUser = () => useContext(DemoUserContext)

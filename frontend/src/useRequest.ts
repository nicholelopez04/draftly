import { useEffect, useState } from 'react'
import { errorMessage } from './api'

type Result<T> = { state: 'loading' } | { state: 'error'; message: string } |
  { state: 'ready'; data: T }

export function useRequest<T>(load: (signal: AbortSignal) => Promise<T>) {
  const [result, setResult] = useState<Result<T>>({ state: 'loading' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    load(controller.signal).then(
      (data) => {
        if (!controller.signal.aborted) setResult({ state: 'ready', data })
      },
      (error: unknown) => {
        if (!controller.signal.aborted) setResult({ state: 'error', message: errorMessage(error) })
      },
    )
    return () => controller.abort()
  }, [load, attempt])

  return {
    result,
    retry() {
      setResult({ state: 'loading' })
      setAttempt((current) => current + 1)
    },
  }
}

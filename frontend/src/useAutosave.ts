import { useCallback, useEffect, useRef, useState } from 'react'
import { useBlocker } from 'react-router-dom'
import { saveDocument, type Draft, type DraftDocument } from './api'

export function useAutosave(document: DraftDocument) {
  const [status, setStatus] = useState<'saving' | 'saved' | 'error'>('saved')
  const [initialDraft] = useState<Draft>(() => ({ title: document.title, content: document.content }))
  const latest = useRef(initialDraft)
  const saved = useRef(initialDraft)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const inFlight = useRef<Promise<boolean> | null>(null)
  const { id } = document

  const flush = useCallback(() => {
    clearTimeout(timer.current)
    if (inFlight.current) return inFlight.current
    if (latest.current === saved.current) return Promise.resolve(true)

    setStatus('saving')
    inFlight.current = (async () => {
      try {
        // Serialize requests so an older save can never overwrite a newer draft.
        while (saved.current !== latest.current) {
          const snapshot = latest.current
          await saveDocument(id, snapshot)
          saved.current = snapshot
        }
        setStatus('saved')
        return true
      } catch {
        setStatus('error')
        return false
      } finally {
        inFlight.current = null
      }
    })()
    return inFlight.current
  }, [id])

  function update(change: Partial<Draft>) {
    latest.current = { ...latest.current, ...change }
    setStatus('saving')
    clearTimeout(timer.current)
    timer.current = setTimeout(() => void flush(), 650)
  }

  const blocker = useBlocker(() => latest.current !== saved.current)
  useEffect(() => {
    if (blocker.state !== 'blocked') return
    let active = true
    void flush().then((success) => {
      if (!active) return
      if (success) blocker.proceed()
      else blocker.reset()
    })
    return () => { active = false }
  }, [blocker, flush])

  useEffect(() => {
    function beforeUnload(event: BeforeUnloadEvent) {
      if (latest.current === saved.current) return
      event.preventDefault()
      event.returnValue = true
    }
    window.addEventListener('beforeunload', beforeUnload)
    return () => {
      clearTimeout(timer.current)
      window.removeEventListener('beforeunload', beforeUnload)
    }
  }, [])

  return { status, update, flush }
}

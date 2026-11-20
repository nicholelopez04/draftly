import { useCallback, useEffect, useRef, useState } from 'react'
import { errorMessage, grantShare, listDemoUsers, listShares, revokeShare } from './api'
import { Loading, RequestError } from './components'
import { useRequest } from './useRequest'

export function ShareDialog({ id, userId, close }: { id: string; userId: number; close: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [pending, setPending] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const load = useCallback(async (signal: AbortSignal) => {
    const [users, shares] = await Promise.all([listDemoUsers(userId, signal), listShares(userId, id, signal)])
    return { users: users.filter((user) => user.id !== userId), shares }
  }, [id, userId])
  const { result, retry } = useRequest(load)

  useEffect(() => { dialog.current?.showModal() }, [])

  async function changeAccess(recipientId: number, name: string, shared: boolean) {
    setPending(true)
    setError('')
    setNotice('')
    try {
      await (shared ? revokeShare : grantShare)(userId, id, recipientId)
      setNotice(shared ? `Removed access for ${name}.` : `Shared with ${name}.`)
      retry()
    } catch (cause) {
      setError(errorMessage(cause))
    } finally {
      setPending(false)
    }
  }

  return (
    <dialog ref={dialog} className="share-dialog panel" aria-labelledby="share-heading" onClose={close}>
      <h2 id="share-heading">Share document</h2>
      <p>Give a demo user read-only access.</p>
      {result.state === 'loading' && <Loading label="Loading sharing settings…" />}
      {result.state === 'error' && <RequestError message={result.message} retry={retry} />}
      {result.state === 'ready' && <ul>
        {result.data.users.map((user) => {
          const shared = result.data.shares.some((share) => share.user_id === user.id)
          return (
            <li className="share-user" key={user.id}>
              <span>{user.name}{shared && <small>Read Only</small>}</span>
              <button className="secondary-button" disabled={pending}
                onClick={() => void changeAccess(user.id, user.name, shared)}>
                {pending ? 'Updating…' : shared ? 'Revoke access' : 'Share'}
              </button>
            </li>
          )
        })}
      </ul>}
      {notice && <p role="status">{notice}</p>}
      {error && <p role="alert" className="error-banner">{error}</p>}
      <form method="dialog"><button className="secondary-button">Done</button></form>
    </dialog>
  )
}

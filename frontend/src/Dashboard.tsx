import { ArrowUpRight, FileText, Plus, Upload } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { createDocument, errorMessage, importDocument, listDocuments, maxImportBytes } from './api'
import { Brand, Loading, RequestError } from './components'
import { useDemoUser } from './demoUser'
import { useRequest } from './useRequest'

const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

export function Dashboard() {
  const { userId } = useDemoUser()
  return <DashboardWorkspace key={userId} />
}

function DashboardWorkspace() {
  const { userId, switchUser } = useDemoUser()
  const load = useCallback((signal: AbortSignal) => listDocuments(userId, signal), [userId])
  const { result, retry } = useRequest(load)
  const [action, setAction] = useState<'create' | 'import' | null>(null)
  const [actionError, setActionError] = useState('')
  const fileInput = useRef<HTMLInputElement>(null)
  const activeAction = useRef<AbortController | null>(null)
  const navigate = useNavigate()
  const [search] = useSearchParams()
  const shared = search.get('view') === 'shared'
  const heading = shared ? 'Shared With Me' : 'My Documents'
  const documents = result.state === 'ready'
    ? result.data.filter((document) => (document.owner_id !== userId) === shared)
    : []

  useEffect(() => () => activeAction.current?.abort(), [])

  async function openNewDocument(file?: File) {
    if (activeAction.current) return
    const controller = new AbortController()
    activeAction.current = controller
    setAction(file ? 'import' : 'create')
    setActionError('')
    try {
      if (file && !/\.(txt|md)$/i.test(file.name)) throw new Error('Choose a .txt or .md file.')
      if (file && file.size > maxImportBytes) throw new Error('The file exceeds the 1 MB limit.')
      const document = await (file
        ? importDocument(userId, file, controller.signal)
        : createDocument(userId, controller.signal))
      if (!controller.signal.aborted) {
        await navigate(`/documents/${document.id}`, { state: { imported: Boolean(file) } })
      }
    } catch (error) {
      if (!controller.signal.aborted) setActionError(errorMessage(error))
    } finally {
      activeAction.current = null
      if (!controller.signal.aborted) setAction(null)
    }
  }

  const createButton = (
    <button className="primary-button" onClick={() => void openNewDocument()} disabled={action !== null}>
      <Plus size={18} aria-hidden="true" />
      {action === 'create' ? 'Creating…' : 'Create Document'}
    </button>
  )

  return (
    <div className="workspace">
      <aside className="sidebar">
        <Brand />
        <nav aria-label="Workspace">
          <Link className="sidebar-link" to="/" aria-current={!shared ? 'page' : undefined}>My Documents</Link>
          <Link className="sidebar-link" to="/?view=shared" aria-current={shared ? 'page' : undefined}>Shared With Me</Link>
        </nav>
        <label className="profile demo-switcher">
          <strong>Switch demo user</strong>
          <select value={userId} disabled={action !== null} onChange={(event) => switchUser(Number(event.target.value))}>
            <option value={1}>Alex Morgan</option>
            <option value={2}>Jordan Lee</option>
          </select>
          <small>Demo only · No authentication</small>
        </label>
      </aside>

      <main className="dashboard">
        <header className="dashboard-header">
          <div>
            <h1>{heading}</h1>
          </div>
          {!shared && <div className="document-actions">
            <input
              ref={fileInput} type="file" accept=".txt,.md" hidden
              onChange={(event) => {
                const file = event.currentTarget.files?.[0]
                event.currentTarget.value = ''
                if (file) void openNewDocument(file)
              }}
            />
            <button className="secondary-button" disabled={action !== null} onClick={() => fileInput.current?.click()}>
              <Upload size={18} aria-hidden="true" />
              {action === 'import' ? 'Importing…' : 'Import Document'}
            </button>
            {createButton}
          </div>}
        </header>

        {actionError && <p className="error-banner" role="alert">{actionError}</p>}
        {result.state === 'loading' && <Loading label="Loading documents…" />}
        {result.state === 'error' && <RequestError message={result.message} retry={retry} />}
        {result.state === 'ready' && (documents.length === 0 ? (
          <section className="panel empty-state">
            <span className="empty-icon"><FileText size={29} aria-hidden="true" /></span>
            <h2>{shared ? 'No documents shared with you' : 'No documents yet'}</h2>
            {!shared && <p>Create or import a document to start writing.</p>}
          </section>
        ) : (
          <section aria-labelledby="recent-title" className="panel document-list">
            <h2 id="recent-title">Recently edited</h2>
            <ul>
              {documents.map((document) => (
                <li key={document.id}>
                  <Link to={`/documents/${document.id}`} className="document-row">
                    <span className="document-icon"><FileText size={20} aria-hidden="true" /></span>
                    <span className="document-meta">
                      <strong>{document.title}</strong>
                      {shared && <small>{document.owner_name} · Read Only</small>}
                      <time dateTime={document.updated_at}>{dateFormat.format(new Date(document.updated_at))}</time>
                    </span>
                    <ArrowUpRight size={17} aria-hidden="true" className="document-arrow" />
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </main>
    </div>
  )
}

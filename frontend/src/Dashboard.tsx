import { ArrowUpRight, FileText, FolderOpen, Plus } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { createDocument, errorMessage, listDocuments } from './api'
import { Brand, Loading, RequestError } from './components'
import { useRequest } from './useRequest'

const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

export function Dashboard() {
  const { result, retry } = useRequest(listDocuments)
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState('')
  const navigate = useNavigate()

  async function create() {
    setCreating(true)
    setCreateError('')
    try {
      const document = await createDocument()
      await navigate(`/documents/${document.id}`)
    } catch (error) {
      setCreateError(errorMessage(error))
      setCreating(false)
    }
  }

  const createButton = (
    <button className="primary-button" onClick={() => void create()} disabled={creating}>
      <Plus size={18} aria-hidden="true" />
      {creating ? 'Creating…' : 'Create Document'}
    </button>
  )

  return (
    <div className="workspace">
      <aside className="sidebar">
        <Brand />
        <nav aria-label="Workspace">
          <Link className="sidebar-link" to="/" aria-current="page">
            <FolderOpen size={19} aria-hidden="true" /> Documents
          </Link>
        </nav>
        <div className="profile">
          <span className="avatar" aria-hidden="true">AM</span>
          <span><strong>Alex Morgan</strong><small>Personal workspace</small></span>
        </div>
      </aside>

      <main className="dashboard">
        <header className="dashboard-header">
          <div>
            <h1>Documents</h1>
            <p>Create, edit, and pick up where you left off.</p>
          </div>
          {createButton}
        </header>

        {createError && <p className="error-banner" role="alert">{createError}</p>}
        {result.state === 'loading' && <Loading label="Loading documents…" />}
        {result.state === 'error' && <RequestError message={result.message} retry={retry} />}
        {result.state === 'ready' && (result.data.length === 0 ? (
          <section className="panel empty-state">
            <span className="empty-icon"><FileText size={29} aria-hidden="true" /></span>
            <h2>No documents yet</h2>
            <p>Create your first document to start writing.</p>
            <button className="secondary-button" onClick={() => void create()} disabled={creating}>
              <Plus size={17} aria-hidden="true" /> {creating ? 'Creating…' : 'Create Document'}
            </button>
          </section>
        ) : (
          <section aria-labelledby="recent-title" className="panel document-list">
            <h2 id="recent-title">Recently edited</h2>
            <ul>
              {result.data.map((document) => (
                <li key={document.id}>
                  <Link to={`/documents/${document.id}`} className="document-row">
                    <span className="document-icon"><FileText size={20} aria-hidden="true" /></span>
                    <span className="document-meta">
                      <strong>{document.title}</strong>
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

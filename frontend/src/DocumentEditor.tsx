import { EditorContent, useEditor, useEditorState, type Editor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import {
  ArrowLeft, Bold, CloudCheck, Heading1, Heading2, Italic, List, ListOrdered,
  LoaderCircle, TriangleAlert, Underline,
} from 'lucide-react'
import { useCallback, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { getDocument, type DraftDocument } from './api'
import { Loading, RequestError } from './components'
import { useDemoUser } from './demoUser'
import { ShareDialog } from './ShareDialog'
import { useAutosave } from './useAutosave'
import { useRequest } from './useRequest'

const tools = [
  { label: 'Bold', icon: Bold, active: (e: Editor) => e.isActive('bold'), run: (e: Editor) => e.chain().focus().toggleBold().run() },
  { label: 'Italic', icon: Italic, active: (e: Editor) => e.isActive('italic'), run: (e: Editor) => e.chain().focus().toggleItalic().run() },
  { label: 'Underline', icon: Underline, active: (e: Editor) => e.isActive('underline'), run: (e: Editor) => e.chain().focus().toggleUnderline().run() },
  { label: 'Heading 1', icon: Heading1, active: (e: Editor) => e.isActive('heading', { level: 1 }), run: (e: Editor) => e.chain().focus().toggleHeading({ level: 1 }).run() },
  { label: 'Heading 2', icon: Heading2, active: (e: Editor) => e.isActive('heading', { level: 2 }), run: (e: Editor) => e.chain().focus().toggleHeading({ level: 2 }).run() },
  { label: 'Bullet list', icon: List, active: (e: Editor) => e.isActive('bulletList'), run: (e: Editor) => e.chain().focus().toggleBulletList().run() },
  { label: 'Numbered list', icon: ListOrdered, active: (e: Editor) => e.isActive('orderedList'), run: (e: Editor) => e.chain().focus().toggleOrderedList().run() },
]

function FormattingBar({ editor }: { editor: Editor }) {
  const active = useEditorState({
    editor,
    selector: ({ editor }) => tools.map((tool) => tool.active(editor)),
  })

  return (
    <div className="formatting" role="group" aria-label="Text formatting">
      {tools.map(({ label, icon: Icon, run }, index) => (
        <button
          key={label}
          type="button"
          aria-label={label}
          title={label}
          aria-pressed={active[index]}
          onMouseDown={(event) => event.preventDefault()}
          onClick={() => run(editor)}
        >
          <Icon size={18} aria-hidden="true" />
        </button>
      ))}
    </div>
  )
}

function EditorForm({ document, userId }: { document: DraftDocument; userId: number }) {
  const [title, setTitle] = useState(document.title)
  const [sharing, setSharing] = useState(false)
  const { state } = useLocation()
  const owned = document.owner_id === userId
  const { status, update, flush } = useAutosave(document, userId)
  const editor = useEditor({
    extensions: [StarterKit.configure({ heading: { levels: [1, 2] } })],
    content: document.content,
    editable: owned,
    editorProps: { attributes: {
      role: 'textbox', 'aria-label': 'Document body', 'aria-multiline': 'true',
      'aria-readonly': String(!owned), ...(owned ? { 'data-placeholder': 'Start writing…' } : {}),
    } },
    onUpdate: ({ editor }) => {
      if (owned) update({ content: editor.getJSON() })
    },
  })

  return (
    <>
      <header className="editor-header">
        <BackLink shared={!owned} />
        {owned ? (
          <div className="document-actions">
            <div className={`save-indicator ${status}`}>
              <span role="status">
                {status === 'saving' && <><LoaderCircle className="animate-spin" size={17} aria-hidden="true" /> Saving…</>}
                {status === 'saved' && <><CloudCheck size={18} aria-hidden="true" /> Saved</>}
                {status === 'error' && <><TriangleAlert size={17} aria-hidden="true" /> Couldn’t save</>}
              </span>
              {status === 'error' && <button onClick={() => void flush()}>Retry</button>}
            </div>
            <button className="secondary-button" onClick={() => setSharing(true)}>Share</button>
          </div>
        ) : <span className="save-indicator">{document.owner_name} · Read Only</span>}
      </header>
      <main className="editor-main">
        {owned && state?.imported && <p className="import-notice" role="status">Document imported.</p>}
        <div className="paper">
          <label className="sr-only" htmlFor="document-title">Document title</label>
          <input
            id="document-title"
            className="document-title"
            placeholder="Untitled document"
            value={title}
            maxLength={200}
            readOnly={!owned}
            onChange={(event) => {
              setTitle(event.target.value)
              update({ title: event.target.value })
            }}
            onBlur={() => { if (owned) setTitle((value) => value.trim() || 'Untitled document') }}
          />
          {owned && editor && <FormattingBar editor={editor} />}
          <EditorContent editor={editor} />
        </div>
      </main>
      {sharing && <ShareDialog id={document.id} userId={userId} close={() => setSharing(false)} />}
    </>
  )
}

function BackLink({ shared = false }: { shared?: boolean }) {
  return <Link className="back-link" to={shared ? '/?view=shared' : '/'}>
    <ArrowLeft size={18} aria-hidden="true" /> {shared ? 'Shared With Me' : 'Documents'}
  </Link>
}

function LoadedDocument({ id, userId }: { id: string; userId: number }) {
  const load = useCallback((signal: AbortSignal) => getDocument(userId, id, signal), [id, userId])
  const { result, retry } = useRequest(load)
  if (result.state === 'ready') return <EditorForm document={result.data} userId={userId} />
  return (
    <>
      <header className="editor-header"><BackLink /></header>
      <main className="editor-main">
        {result.state === 'loading'
          ? <Loading label="Opening document…" />
          : <RequestError message={result.message} retry={retry} />}
      </main>
    </>
  )
}

export function DocumentRoute() {
  const { id } = useParams()
  const { userId } = useDemoUser()
  return <LoadedDocument key={`${userId}:${id}`} id={id!} userId={userId} />
}

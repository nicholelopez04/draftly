import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { createServer } from 'vite'

const vite = await createServer({
  configFile: false,
  envDir: false,
  appType: 'custom',
  server: { middlewareMode: true, ws: false },
})
after(() => vite.close())

const { restoreDemoUser, persistDemoUser, migrateDemoUser } = await vite.ssrLoadModule('/src/demoUser.ts')
const { getDocument, errorMessage } = await vite.ssrLoadModule('/src/api.ts')

function storage(initialUser) {
  const values = new Map(initialUser ? [['draftly-demo-user', initialUser]] : [])
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
  }
}

test('restores a legacy tab selection and migrates it for new tabs', (t) => {
  const localStorage = storage()
  globalThis.window = { localStorage, sessionStorage: storage('2') }
  t.after(() => { delete globalThis.window })
  assert.equal(restoreDemoUser(), 2)
  migrateDemoUser()
  globalThis.window = { localStorage, sessionStorage: storage() }
  assert.equal(restoreDemoUser(), 2)
  persistDemoUser(1)
  globalThis.window = { localStorage, sessionStorage: storage('2') }
  migrateDemoUser()
  assert.equal(restoreDemoUser(), 1)
})

test('loads a direct document URL with the restored identity and can retry a failed request', async (t) => {
  const localStorage = storage()
  globalThis.window = { localStorage, sessionStorage: storage() }
  t.after(() => { delete globalThis.window })
  assert.equal(restoreDemoUser(), 1)
  persistDemoUser(2)
  globalThis.window = { localStorage, sessionStorage: storage() }

  const document = { id: '00000000-0000-4000-8000-000000000001', owner_id: 2 }
  let failNetwork = true
  const fetch = t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(new URL(url).pathname, `/documents/${document.id}`)
    if (failNetwork) throw new TypeError('Network error')
    if (options.headers.get('X-Demo-User-Id') !== '2') {
      return Response.json({ detail: 'Document not found.' }, { status: 404 })
    }
    return Response.json(document)
  })
  const load = () => getDocument(restoreDemoUser(), document.id, new AbortController().signal)
  await assert.rejects(load, (error) => errorMessage(error) === 'Could not reach the Draftly server.')
  failNetwork = false
  assert.deepEqual(await load(), document)
  persistDemoUser(1)
  await assert.rejects(load, /unavailable to the selected demo user/)
  assert.deepEqual(fetch.mock.calls.map(({ arguments: [, options] }) =>
    options.headers.get('X-Demo-User-Id')), ['2', '2', '1'])
})

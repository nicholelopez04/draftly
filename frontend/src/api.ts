import type { JSONContent } from '@tiptap/react'

export interface DocumentSummary {
  id: string
  owner_id: number
  owner_name: string
  title: string
  created_at: string
  updated_at: string
}

export interface Draft {
  title: string
  content: JSONContent
}

export interface DraftDocument extends DocumentSummary, Draft {}

export interface DemoUser {
  id: number
  name: string
}

export interface DocumentShare {
  document_id: string
  user_id: number
  created_at: string
}

export const maxImportBytes = 1024 * 1024

const apiUrl = (
  import.meta.env.VITE_API_BASE_URL?.trim() || import.meta.env.VITE_API_URL || 'http://localhost:8000'
).replace(/\/+$/, '')

class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(userId: number, path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers)
  headers.set('X-Demo-User-Id', String(userId))
  if (typeof options?.body === 'string') headers.set('Content-Type', 'application/json')
  const response = await fetch(apiUrl + path, {
    ...options,
    headers,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(
      response.status,
      typeof body?.detail === 'string' ? body.detail :
        body?.detail?.[0]?.msg || `Request failed (${response.status}).`,
    )
  }
  return response.status === 204 ? undefined as T : response.json() as Promise<T>
}

const documentPath = (id: string) => `/documents/${encodeURIComponent(id)}`

export const listDocuments = (userId: number, signal: AbortSignal) =>
  request<DocumentSummary[]>(userId, '/documents', { signal })

export const createDocument = (userId: number, signal: AbortSignal) =>
  request<DraftDocument>(userId, '/documents', { method: 'POST', body: '{}', signal })

export const importDocument = (userId: number, file: File, signal: AbortSignal) =>
  request<DraftDocument>(userId, `/documents/import?${new URLSearchParams({ filename: file.name })}`, {
    method: 'POST', body: file, headers: { 'Content-Type': 'application/octet-stream' }, signal,
  })

export async function getDocument(userId: number, id: string, signal: AbortSignal) {
  try {
    return await request<DraftDocument>(userId, documentPath(id), { signal })
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      throw new Error('Document not found or unavailable to the selected demo user.')
    }
    throw error
  }
}

export const saveDocument = (userId: number, id: string, draft: Draft) =>
  request<DraftDocument>(userId, documentPath(id), {
    method: 'PATCH',
    body: JSON.stringify({ ...draft, title: draft.title.trim() || 'Untitled document' }),
    signal: AbortSignal.timeout(10000),
  })

export const listDemoUsers = (userId: number, signal: AbortSignal) =>
  request<DemoUser[]>(userId, '/demo-users', { signal })

export const listShares = (userId: number, id: string, signal: AbortSignal) =>
  request<DocumentShare[]>(userId, `${documentPath(id)}/shares`, { signal })

export const grantShare = (userId: number, id: string, recipientId: number) =>
  request<void>(userId, `${documentPath(id)}/shares`, {
    method: 'POST', body: JSON.stringify({ user_id: recipientId }),
  })

export const revokeShare = (userId: number, id: string, recipientId: number) =>
  request<void>(userId, `${documentPath(id)}/shares/${recipientId}`, { method: 'DELETE' })

export function errorMessage(error: unknown) {
  if (error instanceof TypeError) return 'Could not reach the Draftly server.'
  return error instanceof Error ? error.message : 'Something went wrong.'
}

import type { JSONContent } from '@tiptap/react'

export interface DocumentSummary {
  id: string
  owner_id: number
  title: string
  created_at: string
  updated_at: string
}

export interface Draft {
  title: string
  content: JSONContent
}

export interface DraftDocument extends DocumentSummary, Draft {}

const apiUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl + path, {
    ...options,
    headers: options?.body ? { 'Content-Type': 'application/json' } : undefined,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(
      typeof body?.detail === 'string' ? body.detail : `Request failed (${response.status}).`,
    )
  }
  return response.json() as Promise<T>
}

const documentPath = (id: string) => `/documents/${encodeURIComponent(id)}`

export const listDocuments = (signal: AbortSignal) =>
  request<DocumentSummary[]>('/documents', { signal })

export const createDocument = () =>
  request<DraftDocument>('/documents', { method: 'POST', body: '{}' })

export const getDocument = (id: string, signal: AbortSignal) =>
  request<DraftDocument>(documentPath(id), { signal })

export const saveDocument = (id: string, draft: Draft) =>
  request<DraftDocument>(documentPath(id), {
    method: 'PATCH',
    body: JSON.stringify({ ...draft, title: draft.title.trim() || 'Untitled document' }),
    signal: AbortSignal.timeout(10000),
  })

export function errorMessage(error: unknown) {
  if (error instanceof TypeError) return 'Could not reach the Draftly server.'
  return error instanceof Error ? error.message : 'Something went wrong.'
}

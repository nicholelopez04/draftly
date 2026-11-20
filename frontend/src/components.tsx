import { FileText, LoaderCircle, TriangleAlert } from 'lucide-react'
import { Link } from 'react-router-dom'

export function Brand() {
  return (
    <Link to="/" className="brand">
      <span className="brand-icon"><FileText size={19} aria-hidden="true" /></span>
      Draftly
    </Link>
  )
}

export function Loading({ label }: { label: string }) {
  return (
    <div className="panel message" role="status">
      <LoaderCircle className="animate-spin" size={22} aria-hidden="true" />
      {label}
    </div>
  )
}

export function RequestError({ message, retry }: { message: string; retry: () => void }) {
  return (
    <div className="panel message" role="alert">
      <TriangleAlert size={22} aria-hidden="true" />
      <span>{message}</span>
      <button className="secondary-button" onClick={retry}>Try again</button>
    </div>
  )
}

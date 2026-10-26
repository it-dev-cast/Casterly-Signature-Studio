import { HtmlFrame } from './HtmlFrame'
import { ErrorState, LoadingState } from '../ui/States'

interface SignaturePreviewProps {
  html?: string
  loading?: boolean
  error?: string | null
  recipientName?: string
  onRetry?: () => void
}

/** Shows a generated signature inside a simple "new message" mock, like an email client. */
export function SignaturePreview({ html, loading, error, recipientName, onRetry }: SignaturePreviewProps) {
  return (
    <div className="force-light overflow-hidden rounded-xl border border-slate-200 bg-white" data-testid="signature-preview">
      <div className="flex items-center gap-1.5 border-b border-slate-100 bg-slate-50 px-4 py-2.5">
        <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
        <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
        <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
        <span className="ml-3 text-xs font-medium text-slate-500">New message</span>
      </div>
      <div className="space-y-1 border-b border-slate-100 px-5 py-3 text-xs text-slate-500">
        <p>
          <span className="inline-block w-14 text-slate-400">To</span>client@example.com
        </p>
        <p>
          <span className="inline-block w-14 text-slate-400">Subject</span>Following up
        </p>
      </div>
      <div className="px-5 py-5">
        <p className="mb-5 text-sm leading-relaxed text-slate-600">
          Hi there,
          <br />
          <br />
          Thanks for your time today. Please find the details below.
          <br />
          <br />
          Best regards,
        </p>
        {loading ? (
          <LoadingState label="Generating signature..." className="py-10" />
        ) : error ? (
          <ErrorState message={error} onRetry={onRetry} className="py-8" />
        ) : html ? (
          <HtmlFrame html={html} title={recipientName ? `Signature of ${recipientName}` : 'Signature preview'} />
        ) : (
          <p className="py-8 text-center text-sm text-slate-500">Select an employee to preview their signature.</p>
        )}
      </div>
    </div>
  )
}

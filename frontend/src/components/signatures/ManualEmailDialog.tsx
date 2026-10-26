import { Check, Copy, ExternalLink } from 'lucide-react'
import { useState } from 'react'
import type { SetupLink } from '../../services/api'
import { copyRichHtml, copyText } from '../../utils/clipboard'
import { Button } from '../ui/Button'
import { Modal } from '../ui/Modal'
import { Alert } from '../ui/States'
import { HtmlFrame } from './HtmlFrame'

/**
 * Shown when automatic sending (SMTP) isn't configured. Browsers only allow copying to the
 * clipboard directly from a click, so every copy here is its own button.
 */
export function ManualEmailDialog({ info, onClose }: { info: SetupLink; onClose: () => void }) {
  const [copied, setCopied] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function copy(kind: string, fn: () => Promise<void>) {
    setError(null)
    try {
      await fn()
      setCopied(kind)
      setTimeout(() => setCopied((c) => (c === kind ? null : c)), 2500)
    } catch {
      setError('Copying was blocked by the browser. Select the text and press Ctrl+C instead.')
    }
  }

  const CopyButton = ({ kind, onCopy, label = 'Copy' }: { kind: string; onCopy: () => Promise<void>; label?: string }) => (
    <Button size="sm" variant="secondary" icon={copied === kind ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />} onClick={() => copy(kind, onCopy)}>
      {copied === kind ? 'Copied' : label}
    </Button>
  )

  const mailto = `mailto:${encodeURIComponent(info.email)}?subject=${encodeURIComponent(info.subject)}`

  return (
    <Modal
      open
      onClose={onClose}
      size="lg"
      title="Send the signature email yourself"
      description="Automatic sending isn't set up yet. Copy this ready email and send it from your mail app. It takes 3 steps."
      footer={
        <Button variant="secondary" onClick={onClose}>
          Done
        </Button>
      }
    >
      <div className="space-y-5 text-sm">
        {error && <Alert>{error}</Alert>}

        <div>
          <p className="mb-2 font-semibold text-slate-900">1. Copy the email</p>
          <div className="flex flex-wrap items-center gap-2">
            <Button icon={copied === 'email' ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />} onClick={() => copy('email', () => copyRichHtml(info.email_html))}>
              {copied === 'email' ? 'Email copied' : 'Copy email'}
            </Button>
            <span className="text-slate-500">Copies the message below, including the clickable button and signature.</span>
          </div>
        </div>

        <div>
          <p className="mb-2 font-semibold text-slate-900">2. Open a new email</p>
          <div className="flex flex-wrap items-center gap-2">
            <a className="inline-flex h-8 items-center gap-2 rounded-lg border border-slate-300 bg-surface px-3 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50" href={mailto}>
              <ExternalLink className="h-4 w-4" /> Open mail app
            </a>
            <span className="text-slate-500">or start a new email in Outlook yourself and fill in:</span>
          </div>
          <dl className="mt-3 space-y-2 rounded-lg border border-slate-200 p-3">
            <div className="flex flex-wrap items-center gap-2">
              <dt className="w-16 text-slate-500">To</dt>
              <dd className="flex-1 font-medium text-slate-900">{info.email}</dd>
              <CopyButton kind="to" onCopy={() => copyText(info.email)} />
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <dt className="w-16 text-slate-500">Subject</dt>
              <dd className="flex-1 font-medium text-slate-900">{info.subject}</dd>
              <CopyButton kind="subject" onCopy={() => copyText(info.subject)} />
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <dt className="w-16 text-slate-500">Link</dt>
              <dd className="min-w-0 flex-1 truncate text-brand-700">{info.link}</dd>
              <CopyButton kind="link" onCopy={() => copyText(info.link)} />
            </div>
          </dl>
        </div>

        <div>
          <p className="mb-2 font-semibold text-slate-900">3. Paste and send</p>
          <p className="text-slate-600">
            Click inside the message area, press <kbd className="rounded border border-slate-300 px-1.5 text-xs">Ctrl</kbd> +{' '}
            <kbd className="rounded border border-slate-300 px-1.5 text-xs">V</kbd>, remove any other signature, then click <b>Send</b>.
          </p>
        </div>

        <div>
          <p className="mb-2 font-medium text-slate-700">Preview of the email</p>
          <div className="force-light max-h-[360px] overflow-auto rounded-lg border border-slate-200 bg-white p-3">
            <HtmlFrame html={info.email_html} title="Signature email preview" />
          </div>
        </div>
      </div>
    </Modal>
  )
}

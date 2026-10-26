import { Code2, Copy, Download, Mail, MonitorDown } from 'lucide-react'
import { useState } from 'react'
import { useSignatureActions } from '../../hooks/useSignatureActions'
import type { Signature } from '../../types/api'
import { Button } from '../ui/Button'
import { ConfirmDialog } from '../ui/ConfirmDialog'
import { ManualEmailDialog } from './ManualEmailDialog'
import type { SetupLink } from '../../services/api'

interface Props {
  signature: Signature | undefined
  templateId?: number
  /** Show "Send email" (admins only - it emails the employee their signature + setup link). */
  canSendEmail?: boolean
}

/**
 * Copy / download always use `live_html`: its banner points at the live banner address, so a
 * signature pasted into Outlook once keeps showing whatever banner is published.
 */
export function SignatureActions({ signature, templateId, canSendEmail }: Props) {
  const { busy, copySignature, copyHtml, download, installInOutlook, sendSetupEmail } = useSignatureActions()
  const [confirmSend, setConfirmSend] = useState(false)
  const [manual, setManual] = useState<SetupLink | null>(null)
  const disabled = !signature
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {canSendEmail && (
          <Button icon={<Mail className="h-4 w-4" />} disabled={disabled} loading={busy === 'email'} onClick={() => setConfirmSend(true)}>
            Send email
          </Button>
        )}
        <Button
          variant={canSendEmail ? 'secondary' : 'primary'}
          icon={<Copy className="h-4 w-4" />}
          disabled={disabled}
          loading={busy === 'rich'}
          onClick={() => signature && copySignature(signature.live_html)}
        >
          Copy Signature
        </Button>
        <Button variant="secondary" icon={<Code2 className="h-4 w-4" />} disabled={disabled} loading={busy === 'html'} onClick={() => signature && copyHtml(signature.live_html)}>
          Copy HTML
        </Button>
        <Button
          variant="secondary"
          icon={<Download className="h-4 w-4" />}
          disabled={disabled}
          loading={busy === 'download'}
          onClick={() => signature && download(signature.employee.id, signature.employee.employee_code, templateId)}
        >
          Download Signature HTML
        </Button>
        <Button
          variant="secondary"
          icon={<MonitorDown className="h-4 w-4" />}
          disabled={disabled}
          loading={busy === 'outlook'}
          onClick={() => signature && installInOutlook(signature.employee.id)}
        >
          Install in classic Outlook
        </Button>
      </div>
      <p className="text-xs text-slate-500">
        {canSendEmail ? (
          <>
            <strong className="font-medium text-slate-600">Send email</strong> sends the employee their signature and a
            personal link that sets it up in their Outlook for new emails and replies.
          </>
        ) : (
          <>
            Paste the copied signature into Outlook <strong className="font-medium text-slate-600">once</strong>: new company
            banners then appear in it automatically. The installer is only for classic Outlook for Windows.
          </>
        )}
      </p>

      {signature && (
        <ConfirmDialog
          open={confirmSend}
          title="Send signature email?"
          message={
            <>
              <span className="font-medium text-slate-900">{signature.employee.full_name}</span> will receive their signature
              and a setup link at <span className="font-medium text-slate-900">{signature.employee.email}</span>.
            </>
          }
          confirmLabel="Send email"
          loading={busy === 'email'}
          onCancel={() => setConfirmSend(false)}
          onConfirm={async () => {
            const ready = await sendSetupEmail(signature.employee.id)
            setConfirmSend(false)
            if (ready) setManual(ready)
          }}
        />
      )}
      {manual && <ManualEmailDialog info={manual} onClose={() => setManual(null)} />}
    </div>
  )
}

export function HtmlCode({ html }: { html: string }) {
  return (
    <pre className="max-h-80 overflow-auto rounded-lg bg-code p-4 text-xs leading-relaxed text-code-fg">
      <code>{html.replace(/></g, '>\n<')}</code>
    </pre>
  )
}

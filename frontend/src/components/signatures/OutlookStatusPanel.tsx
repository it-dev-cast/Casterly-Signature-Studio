import { AlertTriangle, CheckCircle2, Circle, Info } from 'lucide-react'
import type { ReactNode } from 'react'
import { useOutlookStatus } from '../../hooks/queries'
import { formatDateTime } from '../../utils/format'

function Line({ tone, children }: { tone: 'ok' | 'info' | 'warn' | 'idle'; children: ReactNode }) {
  const icon = {
    ok: <CheckCircle2 className="h-4 w-4 text-emerald-600" />,
    info: <Info className="h-4 w-4 text-brand-600" />,
    warn: <AlertTriangle className="h-4 w-4 text-amber-600" />,
    idle: <Circle className="h-4 w-4 text-slate-300" />,
  }[tone]
  return (
    <li className="flex items-start gap-2">
      <span className="mt-0.5 shrink-0">{icon}</span>
      <span>{children}</span>
    </li>
  )
}

/**
 * The real Outlook state for one employee, as reported by the add-in / installer.
 * Nothing is assumed: Office add-ins cannot change Outlook's saved default signature,
 * so that is always shown as something the employee chooses in Outlook.
 */
export function OutlookStatusPanel({ employeeId }: { employeeId: number | null }) {
  const status = useOutlookStatus(employeeId)
  const s = status.data
  if (!s) return null
  const a = s.addin

  return (
    <div className="rounded-lg border border-slate-200 p-4" data-testid="outlook-status">
      <p className="mb-2 text-sm font-semibold text-slate-900">Outlook</p>
      <ul className="space-y-1.5 text-sm text-slate-600">
        {a ? (
          <>
            <Line tone="ok">
              Outlook add-in connected
              {a.outlook_display_name && (
                <>
                  {' '}as <b>{a.outlook_display_name}</b> <span className="text-slate-400">({a.outlook_email})</span>
                </>
              )}{' '}
              <span className="text-slate-400">· last used {formatDateTime(a.last_seen_at)}</span>
            </Line>
            {a.last_inserted_at ? (
              <Line tone="ok">
                Signature inserted <span className="text-slate-400">· last {formatDateTime(a.last_inserted_at)}</span>
              </Line>
            ) : (
              <Line tone="idle">Signature not inserted yet</Line>
            )}
            {a.last_status === 'kept_outlook_default' && (
              <Line tone="info">
                The employee has their own default signature in Outlook, so it was kept. They can add the Casterly signature
                with <b>Insert Casterly signature</b>, or choose it in Outlook.
              </Line>
            )}
            {a.last_status === 'error' && (
              <Line tone="warn">
                Outlook reported a problem last time{a.last_detail ? <>: <span className="font-mono text-xs">{a.last_detail}</span></> : '.'}
              </Line>
            )}
          </>
        ) : (
          <Line tone="idle">Outlook add-in not used by this employee yet</Line>
        )}
        {s.classic_installed_at && (
          <Line tone="ok">
            Classic Outlook installer run <span className="text-slate-400">· {formatDateTime(s.classic_installed_at)}</span> (set
            as default on first install)
          </Line>
        )}
        <Line tone="info">
          {s.replace_outlook_signature
            ? 'The signature is added automatically to each new email, reply and forward.'
            : "The signature is added automatically when the employee has no default signature of their own in Outlook."}{' '}
          Outlook's own signature list and default aren't changed. Microsoft doesn't let add-ins manage them.
        </Line>
      </ul>
    </div>
  )
}

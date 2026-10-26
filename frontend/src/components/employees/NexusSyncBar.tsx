import { AlertTriangle, CheckCircle2, RefreshCw } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { useNexusSync } from '../../hooks/queries'
import { friendlyError } from '../../utils/errors'
import { formatDateTime } from '../../utils/format'
import { Button } from '../ui/Button'
import { useToast } from '../ui/Toast'

/** Shows how the nexusAuth employee sync is doing, with a "Sync now" button. */
export function NexusSyncBar() {
  const toast = useToast()
  const { status, syncNow, refreshEmployees } = useNexusSync()
  const data = status.data
  const lastSuccess = data?.last_success_at ?? null

  // When a background sync finishes, show its result in the list straight away.
  const seen = useRef<string | null>(null)
  useEffect(() => {
    if (lastSuccess && seen.current && lastSuccess !== seen.current) void refreshEmployees()
    seen.current = lastSuccess
  }, [lastSuccess, refreshEmployees])

  if (!data) return null

  if (!data.enabled) {
    return (
      <p className="mb-4 rounded-lg border border-slate-200 bg-surface px-4 py-2.5 text-sm text-slate-500">
        nexusAuth sync is off. To load employees from nexusAuth automatically, add <code className="font-mono text-xs">NEXUSAUTH_URL</code>,{' '}
        <code className="font-mono text-xs">NEXUSAUTH_EMAIL</code> and <code className="font-mono text-xs">NEXUSAUTH_PASSWORD</code> to{' '}
        <code className="font-mono text-xs">backend/.env</code> and restart the server.
      </p>
    )
  }

  const run = data.last_run
  const failed = !!run?.error
  async function sync() {
    try {
      const result = await syncNow.mutateAsync()
      const r = result.last_run
      if (r?.error) toast.error(r.error)
      else if (r) {
        const changes = r.created + r.updated + r.deactivated
        toast.success(changes ? `Synced: ${r.created} added, ${r.updated} updated, ${r.deactivated} deactivated.` : 'Already up to date with nexusAuth.')
      }
    } catch (err) {
      toast.error(friendlyError(err, 'Could not sync with nexusAuth.'))
    }
  }

  return (
    <div
      className={`mb-4 rounded-lg border px-4 py-3 text-sm ${failed ? 'border-amber-200 bg-amber-50 text-amber-900' : 'border-brand-200 bg-brand-50 text-brand-900'}`}
      role="status"
      aria-label="nexusAuth sync"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="flex min-w-0 flex-1 items-start gap-2.5">
          {failed ? <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /> : <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-brand-600" />}
          <div className="min-w-0">
            {failed ? (
              <>
                <p className="font-medium">nexusAuth sync failed</p>
                <p className="text-xs">
                  {run!.error}
                  {data.paused && ' Automatic sync is paused so the account is not locked; fix the details and press Sync now.'}
                </p>
              </>
            ) : (
              <>
                <p className="font-medium">Employees sync automatically from nexusAuth</p>
                <p className="text-xs opacity-80">
                  {run ? `${run.total_remote} employees in nexusAuth · last checked ${formatDateTime(run.finished_at)}` : 'Waiting for the first sync…'}
                  {` · checks every ${data.interval_seconds}s. Names, IDs, emails, designation, department, phone, LinkedIn, address and status are edited in nexusAuth.`}
                </p>
              </>
            )}
          </div>
        </div>
        <Button variant="secondary" size="sm" icon={<RefreshCw className="h-4 w-4" />} loading={syncNow.isPending} onClick={sync}>
          Sync now
        </Button>
      </div>
      {!failed && run && run.problems.length > 0 && (
        <details className="mt-2 text-xs">
          <summary className="cursor-pointer font-medium">{run.problems.length} record(s) need attention</summary>
          <ul className="mt-1 list-disc space-y-0.5 pl-5">
            {run.problems.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}

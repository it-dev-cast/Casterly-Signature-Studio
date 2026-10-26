import { Search } from 'lucide-react'
import { useState } from 'react'
import { Badge, type Tone } from '../../components/ui/Badge'
import { Card } from '../../components/ui/Card'
import { SelectField } from '../../components/ui/Field'
import { PageHeader, Pagination, table } from '../../components/ui/Misc'
import { EmptyState, ErrorState, LoadingState } from '../../components/ui/States'
import { useAuditLogs } from '../../hooks/queries'
import { useDebounce } from '../../hooks/useDebounce'
import { friendlyError } from '../../utils/errors'
import { formatDateTime, titleCase } from '../../utils/format'

const ACTIONS = [
  'LOGIN', 'LOGOUT',
  'EMPLOYEE_CREATED', 'EMPLOYEE_UPDATED', 'EMPLOYEE_ACTIVATED', 'EMPLOYEE_DEACTIVATED', 'EMPLOYEE_DELETED',
  'BANNER_CREATED', 'BANNER_UPDATED', 'BANNER_PUBLISHED', 'BANNER_UNPUBLISHED', 'BANNER_ARCHIVED', 'BANNER_DELETED',
  'TEMPLATE_CREATED', 'TEMPLATE_UPDATED', 'TEMPLATE_ACTIVATED',
  'SETTINGS_UPDATED',
]

function toneFor(action: string): Tone {
  if (action.endsWith('PUBLISHED') && !action.includes('UN')) return 'green'
  if (/DELETED|DEACTIVATED|ARCHIVED|UNPUBLISHED/.test(action)) return 'red'
  if (/CREATED|ACTIVATED/.test(action)) return 'blue'
  if (/LOGIN|LOGOUT/.test(action)) return 'gray'
  return 'amber'
}

const PAGE_SIZE = 25

export function AuditPage() {
  const [action, setAction] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const q = useDebounce(search.trim(), 300)
  const logs = useAuditLogs({ action, q, page, page_size: PAGE_SIZE })
  const items = logs.data?.items ?? []

  return (
    <>
      <PageHeader title="Audit Logs" description="Every sign-in and change made in Signature Studio." />
      <Card bodyClassName="">
        <div className="flex flex-col gap-3 border-b border-slate-100 p-4 md:flex-row">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="search"
              autoComplete="off"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1) }}
              placeholder="Search descriptions"
              aria-label="Search audit logs"
              className="h-10 w-full rounded-lg border border-slate-300 pl-9 pr-3 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
            />
          </div>
          <SelectField
            label="Action"
            hideLabel
            value={action}
            onChange={(v) => { setAction(v); setPage(1) }}
            containerClassName="md:w-64"
            options={[{ value: '', label: 'All actions' }, ...ACTIONS.map((a) => ({ value: a, label: titleCase(a) }))]}
          />
        </div>

        {logs.isLoading ? (
          <LoadingState label="Loading audit logs..." />
        ) : logs.isError ? (
          <ErrorState message={friendlyError(logs.error, 'Unable to load audit logs.')} onRetry={() => logs.refetch()} />
        ) : items.length === 0 ? (
          <EmptyState title="No audit logs." description={action || q ? 'Try a different filter.' : 'Activity will appear here.'} />
        ) : (
          <>
            <div className={table.wrap}>
              <table className={table.table}>
                <thead className="bg-slate-50/60">
                  <tr>
                    <th className={table.th}>Time</th>
                    <th className={table.th}>Action</th>
                    <th className={table.th}>Description</th>
                    <th className={`${table.th} hidden md:table-cell`}>User</th>
                    <th className={`${table.th} hidden lg:table-cell`}>Entity</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-surface">
                  {items.map((log) => (
                    <tr key={log.id} className={table.row}>
                      <td className={`${table.td} whitespace-nowrap text-slate-500`}>{formatDateTime(log.created_at)}</td>
                      <td className={`${table.td} whitespace-nowrap`}>
                        <Badge tone={toneFor(log.action)}>{titleCase(log.action)}</Badge>
                      </td>
                      <td className={`${table.td} min-w-64`}>{log.description ?? '—'}</td>
                      <td className={`${table.td} hidden md:table-cell`}>{log.user_email ?? 'System'}</td>
                      <td className={`${table.td} hidden whitespace-nowrap text-slate-500 lg:table-cell`}>
                        {log.entity_type ? `${log.entity_type} #${log.entity_id}` : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={page} pageSize={PAGE_SIZE} total={logs.data?.total ?? 0} onChange={setPage} />
          </>
        )}
      </Card>
    </>
  )
}

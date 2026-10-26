import { Archive, Eye, ImagePlus, Pencil, Plus, Send, Trash2, XCircle } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router'
import { ArchiveConfirmDialog, DeleteBannerDialog, PublishConfirmDialog, UnpublishConfirmDialog } from '../../components/banners/BannerDialogs'
import { BannerEditorDialog } from '../../components/banners/BannerEditorDialog'
import { BannerPreview } from '../../components/banners/BannerPreview'
import { CurrentBannerCard } from '../../components/banners/CurrentBannerCard'
import { BannerStatusBadge } from '../../components/ui/Badge'
import { Button, IconButton } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { DetailList, PageHeader, Segmented, table } from '../../components/ui/Misc'
import { Modal } from '../../components/ui/Modal'
import { EmptyState, ErrorState, LoadingState } from '../../components/ui/States'
import { useToast } from '../../components/ui/Toast'
import { useBanner, useBannerMutations, useBanners } from '../../hooks/queries'
import type { Banner } from '../../types/api'
import { friendlyError } from '../../utils/errors'
import { assetUrl, formatDate, formatDateTime } from '../../utils/format'

type Filter = 'all' | 'DRAFT' | 'PUBLISHED' | 'ARCHIVED'
type Pending = { kind: 'publish' | 'unpublish' | 'archive' | 'delete'; banner: Banner } | null

function BannerViewDialog({ bannerId, onClose }: { bannerId: number; onClose: () => void }) {
  const banner = useBanner(bannerId)
  const b = banner.data
  return (
    <Modal open onClose={onClose} size="lg" title={b ? b.name : 'Banner'} description={b?.title}>
      {banner.isLoading ? (
        <LoadingState label="Loading banner..." />
      ) : banner.isError || !b ? (
        <ErrorState message={friendlyError(banner.error, 'Unable to load the banner.')} />
      ) : (
        <div className="space-y-5">
          <BannerPreview html={b.html} title={`${b.name} preview`} />
          <DetailList
            items={[
              { label: 'Status', value: <BannerStatusBadge status={b.effective_status} /> },
              { label: 'Description', value: b.description },
              { label: 'Target URL', value: b.target_url },
              { label: 'Start date', value: formatDateTime(b.start_date) },
              { label: 'End date', value: formatDateTime(b.end_date) },
              { label: 'Published', value: formatDateTime(b.published_at) },
              { label: 'Created', value: `${formatDateTime(b.created_at)}${b.created_by_email ? ` by ${b.created_by_email}` : ''}` },
              { label: 'Updated', value: formatDateTime(b.updated_at) },
            ]}
          />
        </div>
      )}
    </Modal>
  )
}

export function BannersPage() {
  const toast = useToast()
  const [params, setParams] = useSearchParams()
  const [filter, setFilter] = useState<Filter>('all')
  const banners = useBanners()
  const { publish, unpublish, archive, remove } = useBannerMutations()

  const [editor, setEditor] = useState<{ banner: Banner | null } | null>(() => (params.get('new') ? { banner: null } : null))
  const [viewing, setViewing] = useState<number | null>(null)
  const [pending, setPending] = useState<Pending>(null)

  const all = useMemo(() => banners.data ?? [], [banners.data])
  const publishedRow = all.find((b) => b.status === 'PUBLISHED') ?? null
  const publishedDetail = useBanner(publishedRow?.id ?? null)
  const counts = useMemo(
    () => ({
      all: all.length,
      DRAFT: all.filter((b) => b.status === 'DRAFT').length,
      PUBLISHED: all.filter((b) => b.status === 'PUBLISHED').length,
      ARCHIVED: all.filter((b) => b.status === 'ARCHIVED').length,
    }),
    [all],
  )
  const rows = filter === 'all' ? all : all.filter((b) => b.status === filter)

  function openEditor(banner: Banner | null) {
    setEditor({ banner })
  }

  function closeEditor() {
    setEditor(null)
    if (params.get('new')) setParams({}, { replace: true })
  }

  const actionsBusy = publish.isPending || unpublish.isPending || archive.isPending || remove.isPending

  async function runPending() {
    if (!pending) return
    const { kind, banner } = pending
    const map = {
      publish: { fn: publish, ok: `“${banner.name}” is now published in every employee signature.`, fail: 'Unable to publish banner.' },
      unpublish: { fn: unpublish, ok: 'Banner unpublished. Signatures no longer include a banner.', fail: 'Unable to unpublish banner.' },
      archive: { fn: archive, ok: 'Banner archived.', fail: 'Unable to archive banner.' },
      delete: { fn: remove, ok: 'Banner deleted.', fail: 'Unable to delete banner.' },
    }[kind]
    try {
      await map.fn.mutateAsync(banner.id)
      toast.success(map.ok)
    } catch (err) {
      toast.error(friendlyError(err, map.fail))
    } finally {
      setPending(null)
    }
  }

  const dialogProps = (kind: NonNullable<Pending>['kind']) => ({
    open: pending?.kind === kind,
    bannerName: pending?.banner.name,
    loading: actionsBusy,
    onConfirm: runPending,
    onCancel: () => setPending(null),
  })

  return (
    <>
      <PageHeader
        title="Banners"
        description="One published banner is added to every employee signature automatically."
        actions={
          <Button icon={<Plus className="h-4 w-4" />} onClick={() => openEditor(null)}>
            Create Banner
          </Button>
        }
      />

      <div className="space-y-6">
        <CurrentBannerCard
          title="Current Published Banner"
          description={
            publishedDetail.data && publishedDetail.data.effective_status !== 'PUBLISHED'
              ? publishedDetail.data.effective_status === 'SCHEDULED'
                ? 'Scheduled: it will appear in signatures once its start date is reached.'
                : 'Expired: its end date has passed, so signatures currently have no banner.'
              : 'This banner currently appears in employee signatures.'
          }
          banner={publishedDetail.data ?? null}
          loading={banners.isLoading || (publishedRow !== null && publishedDetail.isLoading)}
          onCreate={() => openEditor(null)}
        />

        <Card
          title="Banner History"
          description="All banners, including drafts and archived banners."
          actions={
            <Segmented
              label="Filter banners"
              value={filter}
              onChange={setFilter}
              options={[
                { value: 'all', label: 'All', count: counts.all },
                { value: 'DRAFT', label: 'Drafts', count: counts.DRAFT },
                { value: 'PUBLISHED', label: 'Published', count: counts.PUBLISHED },
                { value: 'ARCHIVED', label: 'Archived', count: counts.ARCHIVED },
              ]}
            />
          }
          bodyClassName=""
        >
          {banners.isLoading ? (
            <LoadingState label="Loading banners..." />
          ) : banners.isError ? (
            <ErrorState message={friendlyError(banners.error, 'Unable to load banners.')} onRetry={() => banners.refetch()} />
          ) : rows.length === 0 ? (
            <EmptyState
              title={filter === 'DRAFT' ? 'No draft banners.' : filter === 'all' ? 'No banners yet.' : 'No banners in this view.'}
              description="Create a banner, preview it, then publish it to every signature."
              action={
                <Button icon={<ImagePlus className="h-4 w-4" />} onClick={() => openEditor(null)}>
                  Create Banner
                </Button>
              }
            />
          ) : (
            <div className={table.wrap}>
              <table className={table.table}>
                <thead className="bg-slate-50/60">
                  <tr>
                    <th className={table.th}>Banner</th>
                    <th className={table.th}>Status</th>
                    <th className={`${table.th} hidden md:table-cell`}>Created</th>
                    <th className={`${table.th} hidden md:table-cell`}>Published</th>
                    <th className={`${table.th} hidden lg:table-cell`}>Start Date</th>
                    <th className={`${table.th} hidden lg:table-cell`}>End Date</th>
                    <th className={`${table.th} text-right`}>Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-surface">
                  {rows.map((b) => (
                    <tr key={b.id} className={table.row}>
                      <td className={table.td}>
                        <div className="flex items-center gap-3">
                          <img src={assetUrl(b.image_url) ?? ''} alt="" className="h-10 w-24 shrink-0 rounded border border-slate-200 bg-slate-100 object-cover" />
                          <div className="min-w-0">
                            <p className="truncate font-medium text-slate-900">{b.name}</p>
                            <p className="truncate text-xs text-slate-500">{b.title}</p>
                          </div>
                        </div>
                      </td>
                      <td className={table.td}>
                        <BannerStatusBadge status={b.effective_status} />
                      </td>
                      <td className={`${table.td} hidden whitespace-nowrap md:table-cell`}>{formatDate(b.created_at)}</td>
                      <td className={`${table.td} hidden whitespace-nowrap md:table-cell`}>{formatDate(b.published_at)}</td>
                      <td className={`${table.td} hidden whitespace-nowrap lg:table-cell`}>{formatDate(b.start_date)}</td>
                      <td className={`${table.td} hidden whitespace-nowrap lg:table-cell`}>{formatDate(b.end_date)}</td>
                      <td className={`${table.td} whitespace-nowrap text-right`}>
                        <IconButton label={`Preview ${b.name}`} onClick={() => setViewing(b.id)}>
                          <Eye className="h-4 w-4" />
                        </IconButton>
                        {b.status !== 'ARCHIVED' && (
                          <IconButton label={`Edit ${b.name}`} onClick={() => openEditor(b)}>
                            <Pencil className="h-4 w-4" />
                          </IconButton>
                        )}
                        {b.status === 'DRAFT' && (
                          <IconButton label={`Publish ${b.name}`} onClick={() => setPending({ kind: 'publish', banner: b })}>
                            <Send className="h-4 w-4" />
                          </IconButton>
                        )}
                        {b.status === 'PUBLISHED' && (
                          <IconButton label={`Unpublish ${b.name}`} onClick={() => setPending({ kind: 'unpublish', banner: b })}>
                            <XCircle className="h-4 w-4" />
                          </IconButton>
                        )}
                        {b.status !== 'ARCHIVED' && (
                          <IconButton label={`Archive ${b.name}`} onClick={() => setPending({ kind: 'archive', banner: b })}>
                            <Archive className="h-4 w-4" />
                          </IconButton>
                        )}
                        {b.status !== 'PUBLISHED' && (
                          <IconButton label={`Delete ${b.name}`} tone="danger" onClick={() => setPending({ kind: 'delete', banner: b })}>
                            <Trash2 className="h-4 w-4" />
                          </IconButton>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      {editor && <BannerEditorDialog banner={editor.banner} published={publishedRow} onClose={closeEditor} />}
      {viewing !== null && <BannerViewDialog bannerId={viewing} onClose={() => setViewing(null)} />}

      <PublishConfirmDialog
        {...dialogProps('publish')}
        replacing={publishedRow && pending?.banner.id !== publishedRow.id ? publishedRow.name : null}
      />
      <UnpublishConfirmDialog {...dialogProps('unpublish')} />
      <ArchiveConfirmDialog {...dialogProps('archive')} />
      <DeleteBannerDialog {...dialogProps('delete')} />
    </>
  )
}

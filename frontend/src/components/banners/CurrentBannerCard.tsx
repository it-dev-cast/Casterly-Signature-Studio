import { ImagePlus, Pencil, Settings2, XCircle } from 'lucide-react'
import { useState } from 'react'
import { useBannerMutations } from '../../hooks/queries'
import type { Banner, BannerWithHtml } from '../../types/api'
import { friendlyError } from '../../utils/errors'
import { formatDateTime } from '../../utils/format'
import { Button, ButtonLink } from '../ui/Button'
import { BannerStatusBadge } from '../ui/Badge'
import { Card } from '../ui/Card'
import { EmptyState, LoadingState } from '../ui/States'
import { useToast } from '../ui/Toast'
import { UnpublishConfirmDialog } from './BannerDialogs'
import { BannerEditorDialog } from './BannerEditorDialog'
import { BannerPreview } from './BannerPreview'

interface Props {
  title: string
  description?: string
  banner: BannerWithHtml | null | undefined
  loading?: boolean
  /** Show a "Manage Banner" link (used on the overview). */
  showManageLink?: boolean
  onCreate: () => void
}

/** Card showing the published banner with Edit / Unpublish actions. Shared by Overview and Banners pages. */
export function CurrentBannerCard({ title, description, banner, loading, showManageLink, onCreate }: Props) {
  const toast = useToast()
  const { unpublish } = useBannerMutations()
  const [editing, setEditing] = useState<Banner | null>(null)
  const [confirming, setConfirming] = useState(false)

  async function doUnpublish() {
    if (!banner) return
    try {
      await unpublish.mutateAsync(banner.id)
      toast.success('Banner unpublished. Signatures no longer include a banner.')
    } catch (err) {
      toast.error(friendlyError(err, 'Unable to unpublish banner.'))
    } finally {
      setConfirming(false)
    }
  }

  return (
    <Card
      title={title}
      description={description}
      actions={
        banner && (
          <>
            {showManageLink && (
              <ButtonLink to="/admin/banners" size="sm" icon={<Settings2 className="h-4 w-4" />}>
                Manage Banner
              </ButtonLink>
            )}
            <Button variant="secondary" size="sm" icon={<Pencil className="h-4 w-4" />} onClick={() => setEditing(banner)}>
              Edit Banner
            </Button>
            <Button variant="secondary" size="sm" icon={<XCircle className="h-4 w-4" />} onClick={() => setConfirming(true)}>
              Unpublish
            </Button>
          </>
        )
      }
    >
      {loading ? (
        <LoadingState label="Loading banner..." className="py-10" />
      ) : !banner ? (
        <EmptyState
          title="No banner is currently published."
          description="Employee signatures are generated without a banner until you publish one."
          action={
            <Button icon={<ImagePlus className="h-4 w-4" />} onClick={onCreate}>
              Create Banner
            </Button>
          }
        />
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <BannerPreview html={banner.html} title={`${banner.name} preview`} />
          </div>
          <dl className="space-y-3 text-sm">
            <div>
              <dt className="text-slate-500">Banner</dt>
              <dd className="font-medium text-slate-900">{banner.name}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Title</dt>
              <dd className="text-slate-900">{banner.title}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Status</dt>
              <dd className="mt-0.5">
                <BannerStatusBadge status={banner.effective_status} />
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Published</dt>
              <dd className="text-slate-900">{formatDateTime(banner.published_at)}</dd>
            </div>
            {(banner.start_date || banner.end_date) && (
              <div>
                <dt className="text-slate-500">Runs</dt>
                <dd className="text-slate-900">
                  {formatDateTime(banner.start_date, 'Now')} → {formatDateTime(banner.end_date, 'No end date')}
                </dd>
              </div>
            )}
          </dl>
        </div>
      )}

      {editing && <BannerEditorDialog banner={editing} published={banner} onClose={() => setEditing(null)} />}
      <UnpublishConfirmDialog
        open={confirming}
        bannerName={banner?.name}
        loading={unpublish.isPending}
        onConfirm={doUnpublish}
        onCancel={() => setConfirming(false)}
      />
    </Card>
  )
}

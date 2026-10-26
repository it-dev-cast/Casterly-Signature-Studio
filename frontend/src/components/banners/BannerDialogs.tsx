import { ConfirmDialog } from '../ui/ConfirmDialog'
import { Alert } from '../ui/States'

interface BaseProps {
  open: boolean
  loading?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export function PublishConfirmDialog({ bannerName, replacing, ...props }: BaseProps & { bannerName?: string; replacing?: string | null }) {
  return (
    <ConfirmDialog
      {...props}
      title="Publish this banner?"
      message="Publishing this banner will make it appear in employee email signatures."
      confirmLabel="Publish Banner"
    >
      {bannerName && (
        <p>
          Banner: <span className="font-medium text-slate-900">{bannerName}</span>
        </p>
      )}
      {replacing && (
        <Alert tone="warning">
          “{replacing}” is currently published and will be unpublished automatically.
        </Alert>
      )}
      <p className="text-xs text-slate-500">Emails that have already been sent are not changed.</p>
    </ConfirmDialog>
  )
}

export function UnpublishConfirmDialog({ bannerName, ...props }: BaseProps & { bannerName?: string }) {
  return (
    <ConfirmDialog
      {...props}
      tone="danger"
      title="Unpublish this banner?"
      message={
        <>
          {bannerName ? <span className="font-medium text-slate-900">“{bannerName}”</span> : 'This banner'} will be removed from all
          employee signatures. Signatures will have no banner until another one is published.
        </>
      }
      confirmLabel="Unpublish"
    />
  )
}

export function ArchiveConfirmDialog({ bannerName, ...props }: BaseProps & { bannerName?: string }) {
  return (
    <ConfirmDialog
      {...props}
      tone="danger"
      title="Archive this banner?"
      message={<>“{bannerName}” will be archived. Archived banners cannot be edited or published and never appear in signatures.</>}
      confirmLabel="Archive"
    />
  )
}

export function DeleteBannerDialog({ bannerName, ...props }: BaseProps & { bannerName?: string }) {
  return (
    <ConfirmDialog
      {...props}
      tone="danger"
      title="Delete this banner?"
      message={<>“{bannerName}” will be permanently deleted. This cannot be undone.</>}
      confirmLabel="Delete"
    />
  )
}

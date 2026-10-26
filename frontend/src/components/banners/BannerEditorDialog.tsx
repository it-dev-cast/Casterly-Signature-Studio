import { Eye, Send } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useBannerMutations } from '../../hooks/queries'
import { bannersApi } from '../../services/api'
import type { Banner, BannerInput, BannerWithHtml } from '../../types/api'
import { fieldErrors, friendlyError } from '../../utils/errors'
import { fromLocalInput, toLocalInput } from '../../utils/format'
import { isHttpUrl, isImageRef, orNull } from '../../utils/validation'
import { ImageUpload } from '../common/ImageUpload'
import { Button } from '../ui/Button'
import { TextAreaField, TextField } from '../ui/Field'
import { Modal } from '../ui/Modal'
import { Alert } from '../ui/States'
import { useToast } from '../ui/Toast'
import { BannerStatusBadge } from '../ui/Badge'
import { PublishConfirmDialog } from './BannerDialogs'
import { BannerPreview } from './BannerPreview'

interface Values {
  name: string
  title: string
  description: string
  image_url: string
  target_url: string
  start_date: string
  end_date: string
}

function initialValues(b?: Banner | null): Values {
  return {
    name: b?.name ?? '',
    title: b?.title ?? '',
    description: b?.description ?? '',
    image_url: b?.image_url ?? '',
    target_url: b?.target_url ?? '',
    start_date: toLocalInput(b?.start_date),
    end_date: toLocalInput(b?.end_date),
  }
}

export function validateBanner(v: Values): Record<string, string> {
  const e: Record<string, string> = {}
  if (!v.name.trim()) e.name = 'Banner name is required.'
  if (!v.title.trim()) e.title = 'Banner title is required.'
  if (!v.image_url.trim()) e.image_url = 'A banner image is required.'
  else if (!isImageRef(v.image_url.trim())) e.image_url = 'Upload an image or enter a valid image URL.'
  if (v.target_url && !isHttpUrl(v.target_url)) e.target_url = 'Enter a valid URL starting with https://'
  if (v.start_date && !fromLocalInput(v.start_date)) e.start_date = 'Enter a valid start date.'
  if (v.end_date && !fromLocalInput(v.end_date)) e.end_date = 'Enter a valid end date.'
  if (v.start_date && v.end_date && new Date(v.end_date) <= new Date(v.start_date))
    e.end_date = 'End date must be after the start date.'
  return e
}

function toInput(v: Values): BannerInput {
  return {
    name: v.name.trim(),
    title: v.title.trim(),
    description: orNull(v.description),
    image_url: v.image_url.trim(),
    target_url: orNull(v.target_url),
    start_date: fromLocalInput(v.start_date),
    end_date: fromLocalInput(v.end_date),
  }
}

interface Props {
  banner?: BannerWithHtml | Banner | null
  /** The banner currently holding PUBLISHED status, for the publish warning. */
  published?: Banner | null
  onClose: () => void
}

/** Create / edit a banner with a live server-rendered preview. Render only while open. */
export function BannerEditorDialog({ banner, published, onClose }: Props) {
  const toast = useToast()
  const { create, update, publish } = useBannerMutations()
  const [savedId, setSavedId] = useState<number | null>(banner?.id ?? null)
  const [values, setValues] = useState<Values>(() => initialValues(banner))
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [previewHtml, setPreviewHtml] = useState<string | null>(banner && 'html' in banner ? banner.html : null)
  const [previewing, setPreviewing] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)

  const isPublished = banner?.status === 'PUBLISHED'
  const saving = create.isPending || update.isPending
  const busy = saving || publish.isPending

  const set = (key: keyof Values) => (value: string) => {
    setValues((v) => ({ ...v, [key]: value }))
    if (errors[key]) setErrors(({ [key]: _omit, ...rest }) => rest)
  }

  function check(): BannerInput | null {
    const found = validateBanner(values)
    setErrors(found)
    setFormError(null)
    return Object.keys(found).length ? null : toInput(values)
  }

  async function handlePreview() {
    const input = check()
    if (!input) return
    setPreviewing(true)
    try {
      setPreviewHtml((await bannersApi.preview(input)).html)
    } catch (err) {
      setErrors(fieldErrors(err))
      setFormError(friendlyError(err, 'Unable to preview the banner.'))
    } finally {
      setPreviewing(false)
    }
  }

  async function save(): Promise<BannerWithHtml | null> {
    const input = check()
    if (!input) return null
    try {
      const saved = savedId ? await update.mutateAsync({ id: savedId, data: input }) : await create.mutateAsync(input)
      setSavedId(saved.id)
      setPreviewHtml(saved.html)
      return saved
    } catch (err) {
      setErrors(fieldErrors(err))
      setFormError(friendlyError(err, 'Unable to save the banner.'))
      return null
    }
  }

  async function handleSave(e?: FormEvent) {
    e?.preventDefault()
    if (busy) return
    const saved = await save()
    if (!saved) return
    toast.success(isPublished ? 'Banner updated. Signatures now use the new version.' : 'Banner saved as draft.')
    onClose()
  }

  async function handlePublishClick() {
    if (busy) return
    const saved = await save()
    if (saved) setConfirmOpen(true)
  }

  async function confirmPublish() {
    if (!savedId) return
    try {
      await publish.mutateAsync(savedId)
      toast.success('Banner published. It now appears in every employee signature.')
      setConfirmOpen(false)
      onClose()
    } catch (err) {
      setConfirmOpen(false)
      setFormError(friendlyError(err, 'Unable to publish banner.'))
    }
  }

  const replacing = published && published.id !== savedId ? published.name : null

  return (
    <>
      <Modal
        open
        onClose={onClose}
        locked={busy}
        size="xl"
        title={banner ? `Edit banner` : 'Create banner'}
        description={
          isPublished
            ? 'This banner is live. Saved changes apply to every employee signature immediately.'
            : 'Banners are saved as drafts until you publish them.'
        }
        footer={
          <>
            <Button variant="secondary" onClick={onClose} disabled={busy} className="mr-auto">
              Cancel
            </Button>
            <Button variant="secondary" onClick={handlePreview} loading={previewing} disabled={busy} icon={<Eye className="h-4 w-4" />}>
              Preview
            </Button>
            {isPublished ? (
              <Button type="submit" form="banner-form" loading={saving}>
                Save changes
              </Button>
            ) : (
              <>
                <Button variant="secondary" type="submit" form="banner-form" loading={saving && !confirmOpen} disabled={publish.isPending}>
                  Save Draft
                </Button>
                <Button onClick={handlePublishClick} disabled={busy} icon={<Send className="h-4 w-4" />}>
                  Publish
                </Button>
              </>
            )}
          </>
        }
      >
        <div className="grid gap-8 lg:grid-cols-5">
          <form autoComplete="off" id="banner-form" onSubmit={handleSave} noValidate className="space-y-5 lg:col-span-3">
            {formError && <Alert>{formError}</Alert>}
            {banner && (
              <div className="flex items-center gap-2 text-sm text-slate-500">
                Status: <BannerStatusBadge status={banner.effective_status} />
              </div>
            )}
            <div className="grid gap-4 sm:grid-cols-2">
              <TextField label="Banner name" required value={values.name} onChange={set('name')} error={errors.name} hint="Internal name, e.g. “Company Anniversary”." />
              <TextField label="Banner title" required value={values.title} onChange={set('title')} error={errors.title} hint="Used as the image alt text in emails." />
            </div>
            <TextAreaField label="Description" value={values.description} onChange={set('description')} error={errors.description} rows={2} />
            <ImageUpload
              label="Banner image"
              kind="banner"
              required
              value={values.image_url}
              onChange={set('image_url')}
              error={errors.image_url}
              hint="Recommended 1200 × 240 px (shown at 600 px wide). PNG, JPEG, GIF or WebP, max 5 MB."
            />
            <TextField
              label="Target URL"
              value={values.target_url}
              onChange={set('target_url')}
              error={errors.target_url}
              placeholder="https://www.example.com/campaign"
              hint="Where recipients go when they click the banner."
            />
            <div className="grid gap-4 sm:grid-cols-2">
              <TextField label="Start date" type="datetime-local" value={values.start_date} onChange={set('start_date')} error={errors.start_date} hint="Optional. Your local time." />
              <TextField label="End date" type="datetime-local" value={values.end_date} onChange={set('end_date')} error={errors.end_date} hint="Optional. Your local time." />
            </div>
          </form>

          <div className="lg:col-span-2">
            <div className="lg:sticky lg:top-0">
              <p className="mb-2 text-sm font-medium text-slate-700">Preview</p>
              <BannerPreview html={previewHtml} loading={previewing} emptyText="Click “Preview” to render the banner." />
              <p className="mt-2 text-xs text-slate-500">
                Rendered by the same engine that builds employee signatures, so this is exactly what recipients will see.
              </p>
            </div>
          </div>
        </div>
      </Modal>

      <PublishConfirmDialog
        open={confirmOpen}
        bannerName={values.name}
        replacing={replacing}
        loading={publish.isPending}
        onConfirm={confirmPublish}
        onCancel={() => {
          setConfirmOpen(false)
          toast.info('Banner saved as draft.')
        }}
      />
    </>
  )
}

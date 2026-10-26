import { ImageOff } from 'lucide-react'
import { HtmlFrame } from '../signatures/HtmlFrame'
import { LoadingState } from '../ui/States'

interface BannerPreviewProps {
  /** Banner HTML produced by the backend's single banner renderer. */
  html: string | null | undefined
  loading?: boolean
  emptyText?: string
  title?: string
}

/**
 * The ONE banner preview component, used by the admin editor, the banner pages,
 * the overview and the employee signature page. It never builds banner markup
 * itself: it displays the exact HTML the signature engine embeds in emails.
 */
export function BannerPreview({ html, loading, emptyText = 'No banner to preview.', title = 'Banner preview' }: BannerPreviewProps) {
  if (loading) return <LoadingState label="Loading banner..." className="py-8" />
  if (!html) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-slate-300 bg-slate-50 py-8 text-sm text-slate-500">
        <ImageOff className="h-5 w-5 text-slate-400" />
        {emptyText}
      </div>
    )
  }
  return (
    <div className="force-light overflow-hidden rounded-lg border border-slate-200 bg-white p-3" data-testid="banner-preview">
      <div className="max-w-[600px]">
        <HtmlFrame html={html} title={title} minHeight={40} />
      </div>
    </div>
  )
}

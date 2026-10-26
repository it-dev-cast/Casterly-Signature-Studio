import { ImagePlus, Trash2 } from 'lucide-react'
import { useId, useRef, useState } from 'react'
import { uploadsApi, type UploadKind } from '../../services/api'
import { friendlyError } from '../../utils/errors'
import { assetUrl } from '../../utils/format'
import { Button } from '../ui/Button'

interface ImageUploadProps {
  label: string
  kind: UploadKind
  value: string
  onChange: (value: string) => void
  error?: string
  required?: boolean
  hint?: string
}

const MAX_MB = 5

const frameClass: Record<UploadKind, string> = {
  banner: 'h-16 w-full rounded-md sm:w-64',
  photo: 'h-16 w-16 rounded-full',
}

/** Upload an image to the backend (or paste a hosted image URL). Stores the returned path/URL. */
export function ImageUpload({ label, kind, value, onChange, error, required, hint }: ImageUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const urlId = useId()
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const preview = assetUrl(value)

  async function handleFile(file: File | undefined) {
    if (!file) return
    setUploadError(null)
    if (!file.type.startsWith('image/')) return setUploadError('Please choose an image file (PNG, JPEG, GIF or WebP).')
    if (file.size > MAX_MB * 1024 * 1024) return setUploadError(`Images must be smaller than ${MAX_MB} MB.`)
    setUploading(true)
    try {
      const result = await uploadsApi.image(file, kind)
      onChange(result.path)
    } catch (err) {
      setUploadError(friendlyError(err, 'The image could not be uploaded.'))
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  const shownError = uploadError ?? error
  return (
    <div>
      <p className="mb-1.5 text-sm font-medium text-slate-700">
        {label}
        {required && <span className="ml-0.5 text-red-500" aria-hidden="true">*</span>}
      </p>
      <div className={`rounded-lg border ${shownError ? 'border-red-300' : 'border-slate-300'} bg-surface p-3`}>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className={`flex shrink-0 items-center justify-center overflow-hidden bg-slate-100 ${frameClass[kind]}`}>
            {preview ? (
              <img src={preview} alt={`${label} preview`} className={`h-full w-full ${kind === 'banner' ? 'object-contain' : 'object-cover'}`} />
            ) : (
              <ImagePlus className="h-6 w-6 text-slate-400" />
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <input
              ref={inputRef}
              type="file"
              accept="image/png,image/jpeg,image/gif,image/webp"
              className="hidden"
              aria-label={`Upload ${label}`}
              onChange={(e) => handleFile(e.target.files?.[0])}
            />
            <Button variant="secondary" size="sm" loading={uploading} onClick={() => inputRef.current?.click()} icon={<ImagePlus className="h-4 w-4" />}>
              {value ? 'Replace image' : 'Upload image'}
            </Button>
            {value && (
              <Button variant="ghost" size="sm" onClick={() => onChange('')} icon={<Trash2 className="h-4 w-4" />}>
                Remove
              </Button>
            )}
          </div>
        </div>
        <label htmlFor={urlId} className="mt-3 block text-xs text-slate-500">
          …or use a hosted image URL
        </label>
        <input
          id={urlId}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="https://cdn.example.com/image.png"
          className="mt-1 block h-9 w-full rounded-md border border-slate-300 px-3 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
        />
      </div>
      {shownError ? (
        <p className="mt-1.5 text-xs text-red-600">{shownError}</p>
      ) : hint ? (
        <p className="mt-1.5 text-xs text-slate-500">{hint}</p>
      ) : null}
    </div>
  )
}

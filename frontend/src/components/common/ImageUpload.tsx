import { ImagePlus, Trash2 } from 'lucide-react'
import { useRef, useState } from 'react'
import { useUploadRules } from '../../hooks/queries'
import { uploadsApi, type UploadKind } from '../../services/api'
import { friendlyError } from '../../utils/errors'
import { assetUrl } from '../../utils/format'
import { checkImageFile } from '../../utils/imageFile'
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

const frameClass: Record<UploadKind, string> = {
  banner: 'h-16 w-full rounded-md sm:w-64',
  photo: 'h-16 w-16 rounded-full',
}

const kindLabel: Record<UploadKind, string> = { banner: 'Banner', photo: 'Photo' }

/**
 * Upload an image to the backend and store the returned path. The file is checked against the
 * upload rules first, so a wrong size or type shows at once; the backend enforces the same rules.
 * An existing image (including an older hosted URL) is shown and kept until it is replaced.
 */
export function ImageUpload({ label, kind, value, onChange, error, required, hint }: ImageUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const rule = useUploadRules().data?.[kind]
  const preview = assetUrl(value)

  async function handleFile(file: File | undefined) {
    if (!file) return
    setUploadError(null)
    const problem = rule ? await checkImageFile(file, rule, kindLabel[kind]) : null
    if (problem) {
      if (inputRef.current) inputRef.current.value = ''
      return setUploadError(problem)
    }
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
              accept="image/png,image/jpeg"
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
      </div>
      {shownError && <p className="mt-1.5 text-xs text-red-600">{shownError}</p>}
      {(rule || hint) && (
        <p className="mt-1.5 text-xs text-slate-500">{[rule?.hint, hint].filter(Boolean).join(' ')}</p>
      )}
    </div>
  )
}

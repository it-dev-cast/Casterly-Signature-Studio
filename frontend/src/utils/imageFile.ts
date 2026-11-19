import type { UploadRule } from '../types/api'
import { readImageSize } from './imageSize'

const TYPE_NAMES: Record<string, string> = {
  'image/jpeg': 'JPG',
  'image/png': 'PNG',
  'image/gif': 'GIF',
  'image/webp': 'WebP',
  'image/svg+xml': 'SVG',
  'image/bmp': 'BMP',
}
const ALLOWED_TYPES = ['image/jpeg', 'image/png']

function typeName(file: File): string {
  return TYPE_NAMES[file.type] ?? (file.name.split('.').pop()?.toUpperCase() || 'not an image')
}

/**
 * Check a file against an upload rule before uploading, so the error shows at once.
 * Messages match the backend's, which applies the same rules in any case. Returns null if OK.
 */
export async function checkImageFile(file: File, rule: UploadRule, label: string): Promise<string | null> {
  if (file.size > rule.max_kb * 1024) {
    return `${label} must be ${rule.max_kb} KB or smaller. Your file is ${Math.ceil(file.size / 1024)} KB.`
  }
  if (!ALLOWED_TYPES.includes(file.type)) return `${label} must be a JPG or PNG image. Your file is ${typeName(file)}.`
  let size: { width: number; height: number }
  try {
    size = await readImageSize(file)
  } catch {
    return 'The file is not a valid image.'
  }
  const { width: w, height: h } = size
  if (rule.exact_width && rule.exact_height && (w !== rule.exact_width || h !== rule.exact_height)) {
    return `${label} must be exactly ${rule.exact_width} x ${rule.exact_height} px. Your image is ${w} x ${h} px.`
  }
  if (rule.min_width && rule.min_height && (w < rule.min_width || h < rule.min_height)) {
    return `${label} must be at least ${rule.min_width} x ${rule.min_height} px. Your image is ${w} x ${h} px.`
  }
  return null
}

/** Client-side checks mirroring the backend rules (the backend remains the authority). */

export const isEmail = (v: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim())

export const isHttpUrl = (v: string) => {
  try {
    const u = new URL(v.trim())
    return (u.protocol === 'http:' || u.protocol === 'https:') && !!u.host
  } catch {
    return false
  }
}

/** Accepts "example.com" (normalised to https:// by the backend). */
export const isWebsite = (v: string) => isHttpUrl(/^https?:\/\//i.test(v) ? v : `https://${v}`)

export const isPhone = (v: string) => /^\+?[0-9()\-.\s]{5,30}$/.test(v.trim()) && (v.match(/\d/g)?.length ?? 0) >= 5

export const isImageRef = (v: string) => v.startsWith('/uploads/') || isHttpUrl(v)

export const isHexColor = (v: string) => /^#[0-9A-Fa-f]{6}$/.test(v)

/** '' -> null so optional fields are sent as null. */
export const orNull = (v: string) => (v.trim() === '' ? null : v.trim())

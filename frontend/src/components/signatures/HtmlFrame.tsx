import { useCallback, useRef, useState } from 'react'
import { useBranding } from '../../hooks/queries'

/**
 * Renders server-generated email HTML in an isolated iframe so app CSS cannot
 * leak in - the result is close to what an email client displays. Scripts are
 * disabled by the sandbox; links open in a new tab.
 *
 * Email HTML points its images at the public address (PUBLIC_BASE_URL) so recipients can
 * load them. For the preview, images from that address are loaded from this app's own
 * server instead, so previews work even when the public address is down or has changed.
 * Only the preview is changed; copied and sent HTML keep the public address.
 */
export function HtmlFrame({ html, title, minHeight = 60 }: { html: string; title: string; minHeight?: number }) {
  const ref = useRef<HTMLIFrameElement>(null)
  const [height, setHeight] = useState(minHeight)

  const measure = useCallback(() => {
    const doc = ref.current?.contentDocument
    if (doc?.body) setHeight(Math.max(minHeight, doc.documentElement.scrollHeight))
  }, [minHeight])

  const publicBase = useBranding().data?.public_base_url
  // `||`, not `??`: VITE_API_BASE_URL is usually set but empty ("use this app's own server").
  const local = import.meta.env.VITE_API_BASE_URL || window.location.origin
  const shown = publicBase ? html.split(`src="${publicBase}/`).join(`src="${local}/`) : html

  const srcDoc =
    '<!DOCTYPE html><html><head><meta charset="utf-8"><base target="_blank">' +
    '<style>html,body{margin:0;padding:0;background:#fff;}body{padding:2px;}</style></head>' +
    `<body>${shown}</body></html>`

  return (
    <iframe
      ref={ref}
      title={title}
      srcDoc={srcDoc}
      onLoad={measure}
      sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"
      className="block w-full border-0 bg-white"
      style={{ height }}
    />
  )
}

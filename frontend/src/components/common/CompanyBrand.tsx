import { assetUrl } from '../../utils/format'
import { useBranding } from '../../hooks/queries'

function LogoTile({ src, size }: { src: string; size: number }) {
  // The logo has a white background, so it always sits on a white tile.
  return (
    <span className="force-light flex shrink-0 items-center justify-center rounded-lg bg-white p-1 ring-1 ring-slate-200" style={{ width: size, height: size }}>
      <img src={src} alt="" className="h-full w-full object-contain" />
    </span>
  )
}

// Shown until the branding has loaded (or if it can't be loaded): the Casterly logo bundled
// with the app, in the same tile as the loaded logo.
const BUNDLED_LOGO = `${import.meta.env.BASE_URL}casterly-logo.png`

function ProductMark({ size }: { size: number }) {
  return <LogoTile src={BUNDLED_LOGO} size={size} />
}

/**
 * Company logo + name from the public /api/branding endpoint, with "Signature Studio" as
 * the product line.
 *  - sidebar: the app sidebar
 *  - topbar:  compact, for the mobile top bar
 *  - login:   large, centred
 */
export function CompanyBrand({ variant = 'sidebar' }: { variant?: 'sidebar' | 'topbar' | 'login' }) {
  const { data } = useBranding()
  const name = data?.company_name
  const logo = assetUrl(data?.company_logo_url)

  if (variant === 'login') {
    return (
      <div className="flex flex-col items-center text-center">
        {logo ? (
          <img src={logo} alt={name ? `${name} logo` : 'Company logo'} className="h-20 w-auto max-w-[200px] object-contain" />
        ) : (
          <ProductMark size={44} />
        )}
        {name && <p className="mt-4 text-sm font-medium text-slate-600">{name}</p>}
      </div>
    )
  }

  const large = variant === 'sidebar'
  return (
    <div className="flex min-w-0 items-center gap-3">
      {logo ? <LogoTile src={logo} size={large ? 38 : 34} /> : <ProductMark size={large ? 38 : 34} />}
      <div className="min-w-0 leading-tight">
        <p className="truncate text-sm font-semibold text-slate-900" title={name}>
          {name ?? 'Signature Studio'}
        </p>
        {name && <p className="truncate text-xs text-slate-500">Signature Studio</p>}
      </div>
    </div>
  )
}

import { X } from 'lucide-react'
import { useEffect, useId, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { IconButton } from './Button'

const widths = { sm: 'max-w-md', md: 'max-w-xl', lg: 'max-w-3xl', xl: 'max-w-5xl' }

// Stack of open modals so Escape only closes the top-most one (e.g. a confirm over an editor).
const openStack: string[] = []

interface ModalProps {
  open: boolean
  onClose: () => void
  title: ReactNode
  description?: ReactNode
  children: ReactNode
  footer?: ReactNode
  size?: keyof typeof widths
  /** Prevent closing (e.g. while a request is running). */
  locked?: boolean
}

export function Modal({ open, onClose, title, description, children, footer, size = 'md', locked }: ModalProps) {
  const titleId = useId()
  const panelRef = useRef<HTMLDivElement>(null)
  const closeRef = useRef(onClose)
  const lockedRef = useRef(locked)
  useEffect(() => {
    closeRef.current = onClose
    lockedRef.current = locked
  })

  useEffect(() => {
    if (!open) return
    const previous = document.activeElement as HTMLElement | null
    openStack.push(titleId)
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !lockedRef.current && openStack[openStack.length - 1] === titleId) closeRef.current()
    }
    document.addEventListener('keydown', onKey)
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    // Focus the first form control, or the panel itself.
    const first = panelRef.current?.querySelector<HTMLElement>('input, select, textarea')
    ;(first ?? panelRef.current)?.focus()
    return () => {
      openStack.splice(openStack.lastIndexOf(titleId), 1)
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = overflow
      previous?.focus?.()
    }
  }, [open, titleId])

  if (!open) return null

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-6">
      <div className="absolute inset-0 bg-black/50" aria-hidden="true" onClick={() => !locked && onClose()} />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className={`relative flex max-h-[92vh] w-full ${widths[size]} flex-col rounded-t-2xl bg-surface shadow-xl outline-none sm:rounded-2xl`}
      >
        <header className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-4">
          <div>
            <h2 id={titleId} className="text-lg font-semibold text-slate-900">
              {title}
            </h2>
            {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
          </div>
          <IconButton label="Close" onClick={onClose} disabled={locked}>
            <X className="h-5 w-5" />
          </IconButton>
        </header>
        <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>
        {footer && (
          <footer className="flex flex-wrap items-center justify-end gap-2 border-t border-slate-100 bg-slate-50/60 px-6 py-4 sm:rounded-b-2xl">
            {footer}
          </footer>
        )}
      </div>
    </div>,
    document.body,
  )
}

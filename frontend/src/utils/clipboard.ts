export function htmlToPlainText(html: string): string {
  const doc = new DOMParser().parseFromString(html, 'text/html')
  doc.querySelectorAll('tr').forEach((tr) => tr.append('\n'))
  return (doc.body.textContent ?? '').replace(/ /g, ' ').replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim()
}

/**
 * Copy the rendered signature so it pastes as formatted content into Outlook / Gmail.
 * Uses the async Clipboard API with text/html when available, otherwise falls back
 * to selecting a hidden rendered copy and using execCommand('copy').
 */
export async function copyRichHtml(html: string): Promise<void> {
  const plain = htmlToPlainText(html)
  if (typeof ClipboardItem !== 'undefined' && navigator.clipboard?.write) {
    try {
      await navigator.clipboard.write([
        new ClipboardItem({
          'text/html': new Blob([html], { type: 'text/html' }),
          'text/plain': new Blob([plain], { type: 'text/plain' }),
        }),
      ])
      return
    } catch {
      // fall through to the selection-based fallback
    }
  }
  const holder = document.createElement('div')
  holder.contentEditable = 'true'
  holder.style.position = 'fixed'
  holder.style.left = '-10000px'
  holder.style.top = '0'
  holder.innerHTML = html // server-generated, escaped signature HTML
  document.body.appendChild(holder)
  const selection = window.getSelection()
  const range = document.createRange()
  range.selectNodeContents(holder)
  selection?.removeAllRanges()
  selection?.addRange(range)
  const ok = document.execCommand('copy')
  selection?.removeAllRanges()
  holder.remove()
  if (!ok) throw new Error('Copy failed')
}

export async function copyText(text: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text)
      return
    } catch {
      // fall through
    }
  }
  const area = document.createElement('textarea')
  area.value = text
  area.style.position = 'fixed'
  area.style.left = '-10000px'
  document.body.appendChild(area)
  area.select()
  const ok = document.execCommand('copy')
  area.remove()
  if (!ok) throw new Error('Copy failed')
}

export function downloadFile(content: string | Blob, filename: string, type = 'text/html') {
  const url = URL.createObjectURL(content instanceof Blob ? content : new Blob([content], { type }))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

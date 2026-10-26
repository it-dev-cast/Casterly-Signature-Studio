import { useState } from 'react'
import { useToast } from '../components/ui/Toast'
import { signaturesApi, type SetupLink } from '../services/api'
import { copyRichHtml, copyText, downloadFile } from '../utils/clipboard'
import { ApiError } from '../services/http'
import { friendlyError } from '../utils/errors'

type Busy = 'rich' | 'html' | 'download' | 'outlook' | 'email' | null

/** Copy / download actions shared by the admin builder and the employee page. */
export function useSignatureActions() {
  const toast = useToast()
  const [busy, setBusy] = useState<Busy>(null)

  async function run(kind: Busy, fn: () => Promise<void>, success: string, failure: string) {
    setBusy(kind)
    try {
      await fn()
      toast.success(success)
    } catch (err) {
      toast.error(friendlyError(err, failure))
    } finally {
      setBusy(null)
    }
  }

  return {
    busy,
    copySignature: (html: string) =>
      run('rich', () => copyRichHtml(html), 'Signature copied successfully.', 'Unable to copy the signature. Try "Copy HTML" instead.'),
    copyHtml: (html: string) =>
      run('html', () => copyText(html), 'Signature HTML copied successfully.', 'Unable to copy the HTML.'),
    download: (employeeId: number, code: string, templateId?: number) =>
      run(
        'download',
        async () => {
          const doc = await signaturesApi.downloadDocument(employeeId, templateId)
          downloadFile(doc, `signature-${code.toLowerCase()}.html`)
        },
        'Signature HTML downloaded.',
        'Unable to download the signature.',
      ),
    installInOutlook: (employeeId: number) =>
      run(
        'outlook',
        async () => {
          const { blob, filename } = await signaturesApi.outlookInstaller(employeeId)
          // The file name carries the installation key, so it must be kept as the server sent it.
          downloadFile(blob, filename ?? 'Casterly-Signature-Setup.exe')
        },
        'Installer downloaded. Run it, then restart Outlook.',
        'Unable to download the Outlook installer.',
      ),
    /**
     * Email the employee their signature + setup link. Returns the ready-made email when automatic
     * sending isn't configured, so the caller can let the admin copy it and send it themselves.
     */
    sendSetupEmail: async (employeeId: number): Promise<SetupLink | null> => {
      setBusy('email')
      try {
        const res = await signaturesApi.sendSetupEmail(employeeId)
        toast.success(`Signature email sent to ${res.email}.`)
        return null
      } catch (err) {
        if (err instanceof ApiError && err.code === 'EMAIL_NOT_CONFIGURED') {
          try {
            return await signaturesApi.setupLink(employeeId)
          } catch (inner) {
            toast.error(friendlyError(inner, 'The signature email could not be prepared.'))
            return null
          }
        }
        toast.error(friendlyError(err, 'The signature email could not be sent.'))
        return null
      } finally {
        setBusy(null)
      }
    },
  }
}

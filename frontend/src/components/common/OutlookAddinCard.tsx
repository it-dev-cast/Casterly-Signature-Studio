import { Download } from 'lucide-react'
import { buttonClasses } from '../ui/Button'
import { Card } from '../ui/Card'
import { Alert } from '../ui/States'

/** Download + setup steps for the Casterly Outlook add-in (new Outlook, web, classic). */
export function OutlookAddinCard({ publicBaseUrl }: { publicBaseUrl: string }) {
  const isPublicHttps = /^https:\/\//i.test(publicBaseUrl) && !/localhost|127\.0\.0\.1/i.test(publicBaseUrl)
  const manifestUrl = `${import.meta.env.VITE_API_BASE_URL ?? ''}/outlook-addin/manifest.xml?download=true`

  return (
    <Card
      title="Outlook add-in"
      description="Adds each person's up-to-date signature to every new email, reply and forward, including the current banner."
    >
      <div className="space-y-4 text-sm text-slate-600">
        {!isPublicHttps && (
          <Alert tone="warning">
            Outlook only loads add-ins from a public <strong>https://</strong> address. The server is currently set to{' '}
            <code className="font-mono">{publicBaseUrl}</code>. Set <code className="font-mono">PUBLIC_BASE_URL</code> to your
            public address (and restart) before downloading the manifest.
          </Alert>
        )}
        <a href={manifestUrl} className={buttonClasses('primary', 'md')} download>
          <Download className="h-4 w-4" /> Download Outlook Add-in Manifest
        </a>
        <div>
          <p className="font-medium text-slate-800">Add it to your Outlook (new Outlook or outlook.office.com)</p>
          <ol className="mt-1 list-decimal space-y-1 pl-4">
            <li>
              Open Outlook and go to <strong>My Add-ins</strong> (on the web you can also open{' '}
              <a className="text-brand-700 underline" href="https://aka.ms/olksideload" target="_blank" rel="noreferrer">
                aka.ms/olksideload
              </a>
              ).
            </li>
            <li>
              Choose <strong>Add a custom add-in</strong> → <strong>Add from File</strong>.
            </li>
            <li>
              Select the downloaded <strong>casterly-signatures-manifest.xml</strong> and click <strong>Install</strong>.
            </li>
            <li>
              Save it in Outlook's list too: <strong>Settings → Accounts → Signatures → + Add signature</strong>, name it{' '}
              <strong>Casterly signature</strong>, paste the employee's copied signature and <strong>Save</strong>.
            </li>
            <li>
              Choose <strong>Casterly signature</strong> for <strong>Default for new messages</strong> and{' '}
              <strong>Default for replies and forwards</strong>, then <strong>Save</strong>. It stays selected.
            </li>
            <li>Click <strong>New mail</strong>. The signature appears after a moment.</li>
          </ol>
        </div>
        <p className="text-xs text-slate-500">
          The add-in never changes or removes anyone's Outlook signatures and never switches Outlook to "no signature". Whether
          it replaces an employee's own default signature is set by the switch in the Company card above.
        </p>
        <p className="text-xs text-slate-500">
          The add-in finds the employee by the email address they're signed in to Outlook with, so each person must exist
          (and be active) in Employees with that exact email. To roll it out to everyone, an IT admin uploads the same
          manifest in the Microsoft 365 admin center → Settings → Integrated apps.
        </p>
      </div>
    </Card>
  )
}

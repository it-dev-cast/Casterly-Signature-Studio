import { useState, type FormEvent } from 'react'
import { OutlookAddinCard } from '../../components/common/OutlookAddinCard'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { TextAreaField, TextField, Toggle } from '../../components/ui/Field'
import { PageHeader } from '../../components/ui/Misc'
import { Alert, ErrorState, LoadingState } from '../../components/ui/States'
import { useToast } from '../../components/ui/Toast'
import { useSettings, useSettingsMutation } from '../../hooks/queries'
import type { AppSettings } from '../../types/api'
import { fieldErrors, friendlyError } from '../../utils/errors'
import { assetUrl, formatDateTime } from '../../utils/format'
import { isWebsite, orNull } from '../../utils/validation'

function SettingsForm({ settings }: { settings: AppSettings }) {
  const toast = useToast()
  const save = useSettingsMutation()
  const [companyName, setCompanyName] = useState(settings.company_name)
  const [website, setWebsite] = useState(settings.company_website ?? '')
  const [showLogo, setShowLogo] = useState(settings.show_logo_in_signature)
  const [replaceOutlook, setReplaceOutlook] = useState(settings.addin_replace_outlook_signature)
  const [disclaimer, setDisclaimer] = useState(settings.legal_disclaimer ?? '')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<string | null>(null)

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (save.isPending) return
    const found: Record<string, string> = {}
    if (!companyName.trim()) found.company_name = 'Company name is required.'
    if (website && !isWebsite(website)) found.company_website = 'Enter a valid website.'
    setErrors(found)
    setFormError(null)
    if (Object.keys(found).length) return
    try {
      await save.mutateAsync({
        company_name: companyName.trim(),
        company_website: orNull(website),
        legal_disclaimer: orNull(disclaimer),
        show_logo_in_signature: showLogo,
        addin_replace_outlook_signature: replaceOutlook,
      })
      toast.success('Settings saved.')
    } catch (err) {
      setErrors(fieldErrors(err))
      setFormError(friendlyError(err, 'Settings could not be saved.'))
    }
  }

  return (
    <form autoComplete="off" onSubmit={submit} noValidate className="space-y-5">
      {formError && <Alert>{formError}</Alert>}
      <TextField label="Company name" required value={companyName} onChange={setCompanyName} error={errors.company_name} hint="Used when an employee has no company set, and as the logo's alt text." />
      <TextField label="Company website" value={website} onChange={setWebsite} error={errors.company_website} hint="Used when an employee has no website set." placeholder="www.example.com" />

      <div>
        <p className="mb-1.5 text-sm font-medium text-slate-700">Company logo</p>
        <div className="flex flex-col gap-4 rounded-lg border border-slate-300 p-4 sm:flex-row sm:items-center">
          <div className="force-light flex h-24 w-24 shrink-0 items-center justify-center rounded-md bg-white p-2 ring-1 ring-slate-200">
            <img src={assetUrl(settings.company_logo_url) ?? ''} alt={`${settings.company_name} logo`} className="h-full w-full object-contain" />
          </div>
          <div className="space-y-2">
            <Toggle
              label="Show logo in email signatures"
              description="Placed on the right, just above the banner, in every employee's signature."
              checked={showLogo}
              onChange={setShowLogo}
            />
            <p className="text-xs text-slate-500">The logo is built into the app and can't be changed here.</p>
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-slate-300 p-4">
        <Toggle
          label="Outlook add-in: use the Casterly signature even if an employee has their own default"
          description={
            replaceOutlook
              ? "On: in each new email the Casterly signature takes the place of the employee's own Outlook signature. Their Outlook settings are not changed."
              : "Off: if an employee has chosen a default signature in Outlook, it is kept. The Casterly signature is added automatically only when no default is set, and is always available from the Insert Casterly signature button."
          }
          checked={replaceOutlook}
          onChange={setReplaceOutlook}
        />
      </div>

      <TextAreaField
        label="Legal disclaimer"
        value={disclaimer}
        onChange={setDisclaimer}
        error={errors.legal_disclaimer}
        rows={3}
        hint="Optional small print shown at the bottom of every signature."
      />
      <div className="flex items-center justify-between gap-4">
        <p className="text-xs text-slate-500">Last updated {formatDateTime(settings.updated_at)}</p>
        <Button type="submit" loading={save.isPending}>
          Save settings
        </Button>
      </div>
    </form>
  )
}

export function SettingsPage() {
  const settings = useSettings()
  return (
    <>
      <PageHeader title="Settings" description="Company-wide defaults applied to every signature." />
      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Company" className="lg:col-span-2">
          {settings.isLoading ? (
            <LoadingState label="Loading settings..." />
          ) : settings.isError || !settings.data ? (
            <ErrorState message={friendlyError(settings.error, 'Unable to load settings.')} onRetry={() => settings.refetch()} />
          ) : (
            <SettingsForm key={settings.data.updated_at} settings={settings.data} />
          )}
        </Card>
        {settings.data && (
          <div className="lg:col-span-2">
            <OutlookAddinCard publicBaseUrl={settings.data.public_base_url} />
          </div>
        )}
        <Card title="About banners and sent email">
          <p className="text-sm leading-relaxed text-slate-600">
            Publishing a banner changes every <strong>newly generated</strong> signature immediately. Emails that have already
            been sent keep the signature they were sent with. Employees pick up the latest version by copying their
            signature again, or automatically once the Outlook / Gmail integrations are enabled.
          </p>
        </Card>
      </div>
    </>
  )
}

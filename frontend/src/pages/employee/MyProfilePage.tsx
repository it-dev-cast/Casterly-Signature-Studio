import { ActiveBadge } from '../../components/ui/Badge'
import { ButtonLink } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Avatar, DetailList, PageHeader } from '../../components/ui/Misc'
import { ErrorState, LoadingState } from '../../components/ui/States'
import { useMyProfile } from '../../hooks/queries'
import { friendlyError } from '../../utils/errors'

export function MyProfilePage() {
  const profile = useMyProfile()
  if (profile.isLoading) return <LoadingState label="Loading profile..." />
  if (profile.isError || !profile.data)
    return <ErrorState message={friendlyError(profile.error, 'Unable to load your profile.')} onRetry={() => profile.refetch()} />
  const e = profile.data

  return (
    <>
      <PageHeader
        title="My Profile"
        description="The information used in your email signature."
        actions={<ButtonLink to="/employee/signature" variant="primary">View my signature</ButtonLink>}
      />
      <Card>
        <div className="mb-5 flex items-center gap-4">
          <Avatar name={e.full_name} src={e.profile_photo_url} size={64} />
          <div>
            <p className="text-lg font-semibold text-slate-900">{e.full_name}</p>
            <p className="text-sm text-slate-500">{e.designation}</p>
            <div className="mt-1">
              <ActiveBadge active={e.is_active} />
            </div>
          </div>
        </div>
        <DetailList
          items={[
            { label: 'Employee ID', value: e.employee_code },
            { label: 'Department', value: e.department },
            { label: 'Company', value: e.company },
            { label: 'Email', value: e.email },
            { label: 'Phone', value: e.phone },
            { label: 'Mobile', value: e.mobile },
            { label: 'Website', value: e.website },
            { label: 'Address', value: e.address },
            { label: 'LinkedIn', value: e.linkedin_url },
            { label: 'X / Twitter', value: e.twitter_url },
            { label: 'Instagram', value: e.instagram_url },
            { label: 'Other', value: e.other_social_url },
          ]}
        />
        <p className="mt-4 text-xs text-slate-500">Your profile is managed by your administrator. Contact them to update any details.</p>
      </Card>
    </>
  )
}

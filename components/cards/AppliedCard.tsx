import type { SlimJob } from '@/lib/slim'

interface Props {
  job: SlimJob
}

export default function AppliedCard({ job }: Props) {
  const status = job.pipeline?.status
  const dateAdded = job.pipeline?.date_added ?? ''
  const dateUpdated = job.pipeline?.date_updated ?? ''

  const daysSinceUpdate = dateUpdated
    ? Math.floor((Date.now() - new Date(dateUpdated).getTime()) / 86400000)
    : 0
  const urgent = daysSinceUpdate > 14

  const isScreen = status === 'recruiter_screen'

  const appliedLabel = dateAdded
    ? `applied ${new Date(dateAdded).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })}`
    : 'applied'

  return (
    <div className="card" tabIndex={0}>
      <div className="card-head">
        <div className="card-name">
          <div className="card-co">{job.company}</div>
          <div className="card-title">{job.title}</div>
        </div>
      </div>
      <div className="card-meta">{job.location.split(',')[0]}</div>
      <div className="card-status">
        {isScreen
          ? <span className="note">recruiter screen</span>
          : <span className="note">{appliedLabel}</span>
        }
      </div>
      {daysSinceUpdate > 7 && (
        <div className={`card-status ${urgent ? 'is-overdue' : 'is-due'}`}>
          <span className={`dot ${urgent ? 'dot--red' : 'dot--accent'}`} />
          <span>{urgent ? 'follow up now' : `${daysSinceUpdate}d since update`}</span>
        </div>
      )}
    </div>
  )
}

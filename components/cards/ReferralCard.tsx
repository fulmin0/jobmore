import type { SlimJob } from '@/lib/slim'

interface Props {
  job: SlimJob
}

function parseReferralFromNotes(notes: string): {
  contact: string | null
  submitted: boolean
  overdueDays: number
} {
  // Try to extract referral info from pipeline notes
  const contactMatch = notes.match(/via\s+([A-Za-z ]+?)(?:\s*[-·,]|$)/i)
  const contact = contactMatch?.[1]?.trim() ?? null
  const submitted = /submitted/i.test(notes)
  return { contact, submitted, overdueDays: 0 }
}

export default function ReferralCard({ job }: Props) {
  const notes = job.pipeline?.notes ?? ''
  const dateUpdated = job.pipeline?.date_updated ?? ''
  const daysSince = dateUpdated
    ? Math.floor((Date.now() - new Date(dateUpdated).getTime()) / 86400000)
    : 0
  const overdue = daysSince > 3

  const { contact, submitted } = parseReferralFromNotes(notes)
  const isSubmitted = job.pipeline?.status === 'referral_submitted' || submitted
  const tone = overdue ? 'is-overdue' : 'is-due'

  return (
    <div className="card" tabIndex={0}>
      <div className="card-head">
        <div className="card-name">
          <div className="card-co">{job.company}</div>
          <div className="card-title">{job.title}</div>
        </div>
      </div>
      <div className="card-meta">{job.location.split(',')[0]}</div>
      <div className={`card-status ${tone}`}>
        <span className={`dot ${overdue ? 'dot--red' : 'dot--accent'}`} />
        {overdue && (
          <span>
            <span className="label">{daysSince}d stale</span>
            {contact && <> · ping {contact}</>}
          </span>
        )}
        {!overdue && isSubmitted && (
          <span><span className="label">submitted</span>{contact && ` · ${contact}`}</span>
        )}
        {!overdue && !isSubmitted && (
          <span>{contact ? `via ${contact}` : 'referral pending'}</span>
        )}
      </div>
    </div>
  )
}

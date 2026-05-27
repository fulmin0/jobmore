import type { SlimJob } from '@/lib/slim'

interface Props {
  job: SlimJob
}

export default function InterviewCard({ job }: Props) {
  const history = job.pipeline?.history ?? []

  // Build round states from pipeline history
  // Count interview-related transitions as rounds
  const interviewEntries = history.filter(h => h.status === 'interview')
  const totalRounds = Math.max(3, interviewEntries.length + 1)
  const doneCount = Math.max(0, interviewEntries.length - 1)

  const rounds: Array<'done' | 'next' | 'pending'> = Array.from(
    { length: totalRounds },
    (_, i) => {
      if (i < doneCount) return 'done'
      if (i === doneCount) return 'next'
      return 'pending'
    }
  )

  const roundNum = doneCount + 1
  const dateUpdated = job.pipeline?.date_updated
  const nextLabel = dateUpdated
    ? `Round ${roundNum} · ${new Date(dateUpdated).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })}`
    : `Round ${roundNum}`

  return (
    <div className="card" tabIndex={0}>
      <div className="card-head">
        <div className="card-name">
          <div className="card-co">{job.company}</div>
          <div className="card-title">{job.title}</div>
        </div>
      </div>
      <div className="card-meta">{job.location.split(',')[0]}</div>
      <div className="card-status is-prep">
        <span className="rounds">
          {rounds.map((r, i) => (
            <span
              key={i}
              className={`round-dot${r === 'done' ? ' round-dot--done' : r === 'next' ? ' round-dot--next' : ''}`}
            />
          ))}
        </span>
        <span className="label">{nextLabel}</span>
      </div>
    </div>
  )
}

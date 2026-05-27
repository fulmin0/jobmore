import type { SlimJob } from '@/lib/slim'

interface Props {
  job: SlimJob
  onShortlist: (id: number) => void
  onSkip: (id: number) => void
}

export default function DiscoverCard({ job, onShortlist, onSkip }: Props) {
  const hi = job.score >= 85

  return (
    <div className="card" tabIndex={0}>
      <div className="card-head">
        <div className="card-name">
          <div className="card-co">{job.company}</div>
          <div className="card-title">{job.title}</div>
        </div>
        <span className={`score${hi ? ' score--hi' : ''}`}>{job.score}</span>
      </div>
      <div className="card-meta">
        {job.location.split(',')[0]}
      </div>
      <div className="card-quick" onClick={e => e.stopPropagation()}>
        <button className="btn btn--ghost btn--small" onClick={() => onSkip(job.id)}>
          skip
        </button>
        <button className="btn btn--primary btn--small" onClick={() => onShortlist(job.id)}>
          + shortlist
        </button>
      </div>
    </div>
  )
}

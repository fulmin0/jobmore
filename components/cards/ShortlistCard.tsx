import type { SlimJob } from '@/lib/slim'

interface Props {
  job: SlimJob
  materialsReady: number
}

export default function ShortlistCard({ job, materialsReady }: Props) {
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
        <span className="materials-text">
          <span className="num">{materialsReady}/5</span> materials ready
        </span>
      </div>
    </div>
  )
}

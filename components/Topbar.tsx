import type { Goal } from '@/lib/types'

interface Props {
  goals: Goal[]
}

function GoalItem({ label, done, target, tone }: Goal) {
  const pct = Math.min(100, (done / target) * 100)
  return (
    <div className={`goal${tone ? ` goal--${tone}` : ''}`}>
      <div className="goal-line">
        <span className="goal-label">{label}</span>
        <span className="goal-num">
          {done}<span className="of">/{target}</span>
        </span>
      </div>
      <div className="goal-bar">
        <i style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

export default function Topbar({ goals }: Props) {
  return (
    <div className="topbar">
      <span className="brand">jobmore</span>
      <div className="goals">
        {goals.map(g => <GoalItem key={g.label} {...g} />)}
      </div>
      <div className="actions">
        <button className="btn btn--primary btn--small">+ Add job</button>
        <button className="icon-btn" aria-label="Settings" title="Settings">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1.03 1.55V21a2 2 0 1 1-4 0v-.09a1.7 1.7 0 0 0-1.11-1.55 1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-1.55-1.03H3a2 2 0 1 1 0-4h.09A1.7 1.7 0 0 0 4.6 8.91a1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.7 1.7 0 0 0 1.87.34H9a1.7 1.7 0 0 0 1.03-1.55V3a2 2 0 1 1 4 0v.09c0 .68.4 1.3 1.03 1.55a1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.7 1.7 0 0 0-.34 1.87V9c.25.63.87 1.03 1.55 1.03H21a2 2 0 1 1 0 4h-.09a1.7 1.7 0 0 0-1.55 1.03Z" />
          </svg>
        </button>
      </div>
    </div>
  )
}

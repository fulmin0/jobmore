import type { StripItem } from '@/lib/types'

interface Props {
  items: StripItem[]
}

export default function ReminderStrip({ items }: Props) {
  if (items.length === 0) return null

  return (
    <div className="strip">
      <span className="strip-label">Due today</span>
      <span className="strip-count">{items.length}</span>
      <div className="strip-items">
        {items.map(item => (
          <span
            key={item.id}
            className={`strip-item${item.overdue ? ' overdue' : ''}`}
          >
            {item.label}
          </span>
        ))}
      </div>
      <button className="strip-link">view all →</button>
    </div>
  )
}

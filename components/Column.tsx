'use client'
import { useDroppable } from '@dnd-kit/core'
import { useDraggable } from '@dnd-kit/core'
import type { BoardColumn } from '@/lib/types'
import type { SlimJob } from '@/lib/slim'
import DiscoverCard from './cards/DiscoverCard'
import ShortlistCard from './cards/ShortlistCard'
import ReferralCard from './cards/ReferralCard'
import AppliedCard from './cards/AppliedCard'
import InterviewCard from './cards/InterviewCard'
import { CSS } from '@dnd-kit/utilities'

interface DraggableCardProps {
  job: SlimJob
  column: BoardColumn
  onShortlist?: (id: number) => void
  onSkip?: (id: number) => void
}

function DraggableCard({ job, column, onShortlist, onSkip }: DraggableCardProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: job.id,
    data: { column },
  })

  const style = transform
    ? { transform: CSS.Translate.toString(transform), zIndex: 999, position: 'relative' as const }
    : undefined

  const cardProps = { ...listeners, ...attributes, ref: setNodeRef, style }

  const inner = (() => {
    switch (column) {
      case 'discover':
        return (
          <DiscoverCard
            job={job}
            onShortlist={onShortlist!}
            onSkip={onSkip!}
          />
        )
      case 'shortlist':
        return <ShortlistCard job={job} materialsReady={0} />
      case 'referral':
        return <ReferralCard job={job} />
      case 'applied':
        return <AppliedCard job={job} />
      case 'interview':
        return <InterviewCard job={job} />
    }
  })()

  return (
    <div
      {...cardProps}
      className={isDragging ? 'card--dragging' : ''}
      style={{ ...style, touchAction: 'none' }}
    >
      {inner}
    </div>
  )
}

interface ColumnProps {
  id: BoardColumn
  title: string
  label: string
  mark: 'red' | 'accent' | 'green' | null
  jobs: SlimJob[]
  maxVisible?: number
  overflowTotal?: number
  onShortlist?: (id: number) => void
  onSkip?: (id: number) => void
}

export default function Column({
  id,
  title,
  label,
  mark,
  jobs,
  maxVisible = 20,
  overflowTotal,
  onShortlist,
  onSkip,
}: ColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id })
  const visible = jobs.slice(0, maxVisible)
  const overflow = overflowTotal ?? (jobs.length - visible.length)

  return (
    <div className="col">
      <div className="col-head">
        <span className="col-title">{title}</span>
        <span className="col-count">{label}</span>
        {mark && (
          <span
            className={`col-mark col-mark--${mark}`}
            title={mark === 'red' ? 'needs attention' : 'upcoming'}
          />
        )}
      </div>
      <div
        ref={setNodeRef}
        className={`col-body${isOver ? ' col-body--over' : ''}`}
      >
        {visible.map(job => (
          <DraggableCard
            key={job.id}
            job={job}
            column={id}
            onShortlist={onShortlist}
            onSkip={onSkip}
          />
        ))}
        {visible.length === 0 && (
          <div className={`empty-slot${isOver ? ' empty-slot--over' : ''}`}>
            drag here
          </div>
        )}
        {overflow > 0 && (
          <button className="col-more">+ {overflow} more</button>
        )}
      </div>
    </div>
  )
}

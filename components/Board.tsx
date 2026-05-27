'use client'
import { useState, useCallback } from 'react'
import { DndContext, DragEndEvent, closestCenter, PointerSensor, useSensor, useSensors } from '@dnd-kit/core'
import type { BoardColumn, Goal, StripItem } from '@/lib/types'
import type { SlimJob } from '@/lib/slim'
import { columnFirstStatus, getColumnMark, getColumnLabel } from '@/lib/board'
import Topbar from './Topbar'
import ReminderStrip from './ReminderStrip'
import Column from './Column'

const COLUMN_ORDER: BoardColumn[] = ['discover', 'shortlist', 'referral', 'applied', 'interview']
const COLUMN_TITLES: Record<BoardColumn, string> = {
  discover: 'Discover',
  shortlist: 'Shortlist',
  referral: 'Referral',
  applied: 'Applied',
  interview: 'Interview',
}

// Discover → any column ok. Other columns cannot move back to discover.
const BLOCKED_TARGETS: Partial<Record<BoardColumn, BoardColumn[]>> = {
  shortlist: ['discover'],
  referral: ['discover'],
  applied: ['discover'],
  interview: ['discover'],
}

interface Props {
  columns: Record<BoardColumn, SlimJob[]>
  goals: Goal[]
  stripItems: StripItem[]
  discoverTotal?: number
}

export default function Board({ columns: initial, goals, stripItems, discoverTotal }: Props) {
  const [columns, setColumns] = useState(initial)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  )

  const handleDragEnd = useCallback(async (event: DragEndEvent) => {
    const { active, over } = event
    if (!over) return

    const jobId = active.id as number
    const targetCol = over.id as BoardColumn

    // Find source column
    let sourceCol: BoardColumn | null = null
    for (const col of COLUMN_ORDER) {
      if (columns[col].some(j => j.id === jobId)) {
        sourceCol = col
        break
      }
    }
    if (!sourceCol || sourceCol === targetCol) return
    if (BLOCKED_TARGETS[sourceCol]?.includes(targetCol)) return

    const job = columns[sourceCol].find(j => j.id === jobId)!
    const newStatus = columnFirstStatus(targetCol)

    // Optimistic update
    setColumns(prev => ({
      ...prev,
      [sourceCol!]: prev[sourceCol!].filter(j => j.id !== jobId),
      [targetCol]: [...prev[targetCol], { ...job, pipeline: { ...job.pipeline, status: newStatus } as SlimJob['pipeline'] }],
    }))

    try {
      await fetch(`/api/jobs/${jobId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pipelineStatus: newStatus }),
      })
    } catch {
      // Revert
      setColumns(prev => ({
        ...prev,
        [targetCol]: prev[targetCol].filter(j => j.id !== jobId),
        [sourceCol!]: [...prev[sourceCol!], job],
      }))
    }
  }, [columns])

  const handleShortlist = useCallback(async (jobId: number) => {
    const job = columns.discover.find(j => j.id === jobId)
    if (!job) return

    setColumns(prev => ({
      ...prev,
      discover: prev.discover.filter(j => j.id !== jobId),
      shortlist: [{ ...job }, ...prev.shortlist],
    }))

    await fetch(`/api/jobs/${jobId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pipelineStatus: 'want_to_apply' }),
    })
  }, [columns.discover])

  const handleSkip = useCallback((jobId: number) => {
    setColumns(prev => ({
      ...prev,
      discover: prev.discover.filter(j => j.id !== jobId),
    }))
  }, [])

  return (
    <div className="app">
      <Topbar goals={goals} />
      <ReminderStrip items={stripItems} />
      <div className="board-wrap">
        <DndContext sensors={sensors} onDragEnd={handleDragEnd} collisionDetection={closestCenter}>
          <div className="board">
            {COLUMN_ORDER.map(col => (
              <Column
                key={col}
                id={col}
                title={COLUMN_TITLES[col]}
                label={getColumnLabel(col, col === 'discover' ? (discoverTotal ?? columns[col].length) : columns[col].length)}
                mark={getColumnMark(col, columns[col])}
                jobs={columns[col]}
                overflowTotal={col === 'discover' && discoverTotal ? discoverTotal - columns[col].length : undefined}
                onShortlist={col === 'discover' ? handleShortlist : undefined}
                onSkip={col === 'discover' ? handleSkip : undefined}
              />
            ))}
          </div>
        </DndContext>
      </div>
    </div>
  )
}

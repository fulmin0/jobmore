import type { RawJob, BoardColumn, Goal, StripItem, PipelineStatus } from './types'
import type { SlimJob } from './slim'

const STALL_DAYS: Partial<Record<PipelineStatus, number>> = {
  want_to_apply: 7,
  content_ready: 5,
  referral_found: 3,
  referral_submitted: 7,
  applied: 14,
  recruiter_screen: 7,
  interview: 5,
}

export function getColumn(job: SlimJob): BoardColumn | null {
  const status = job.pipeline?.status
  if (!status) return 'discover'
  if (status === 'want_to_apply' || status === 'content_ready') return 'shortlist'
  if (status === 'referral_found' || status === 'referral_submitted') return 'referral'
  if (status === 'applied' || status === 'recruiter_screen') return 'applied'
  if (status === 'interview') return 'interview'
  return null
}

export function groupByColumn(jobs: SlimJob[]): Record<BoardColumn, SlimJob[]> {
  const columns: Record<BoardColumn, SlimJob[]> = {
    discover: [],
    shortlist: [],
    referral: [],
    applied: [],
    interview: [],
  }
  for (const job of jobs) {
    const col = getColumn(job)
    if (col) columns[col].push(job)
  }
  columns.discover.sort((a, b) => b.score - a.score)
  return columns
}

export function buildGoals(jobs: SlimJob[]): Goal[] {
  const pipelineStatuses = new Set<PipelineStatus>([
    'want_to_apply', 'content_ready', 'referral_found', 'referral_submitted',
    'applied', 'recruiter_screen', 'interview',
  ])
  const shortlisted = jobs.filter(j => j.pipeline && pipelineStatuses.has(j.pipeline.status)).length

  const stalled = jobs.filter(j => {
    if (!j.pipeline) return false
    const threshold = STALL_DAYS[j.pipeline.status]
    if (!threshold) return false
    const daysSince = (Date.now() - new Date(j.pipeline.date_updated).getTime()) / 86400000
    return daysSince > threshold
  }).length

  return [
    { label: 'shortlist', done: shortlisted, target: 5 },
    { label: 'reminders', done: stalled, target: 4, tone: 'red' },
    { label: 'mock', done: 0, target: 1, tone: 'green' },
  ]
}

export function buildStripItems(jobs: SlimJob[]): StripItem[] {
  const items: StripItem[] = []
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  for (const job of jobs) {
    if (!job.pipeline) continue
    const threshold = STALL_DAYS[job.pipeline.status]
    if (!threshold) continue
    const updated = new Date(job.pipeline.date_updated)
    updated.setHours(0, 0, 0, 0)
    const daysSince = Math.floor((today.getTime() - updated.getTime()) / 86400000)
    if (daysSince >= threshold) {
      const stage = job.pipeline.status.replace(/_/g, ' ')
      items.push({
        id: job.id,
        label: `${job.company} · ${stage}`,
        overdue: daysSince > threshold,
      })
    }
  }

  return items.slice(0, 5)
}

export function columnFirstStatus(col: BoardColumn): PipelineStatus {
  const map: Record<BoardColumn, PipelineStatus> = {
    discover: 'want_to_apply',
    shortlist: 'want_to_apply',
    referral: 'referral_found',
    applied: 'applied',
    interview: 'interview',
  }
  return map[col]
}

export function getColumnMark(col: BoardColumn, jobs: SlimJob[]): 'red' | 'accent' | 'green' | null {
  if (col === 'referral' && jobs.length > 0) {
    const hasOverdue = jobs.some(j => {
      if (!j.pipeline) return false
      const days = (Date.now() - new Date(j.pipeline.date_updated).getTime()) / 86400000
      return days > (STALL_DAYS[j.pipeline.status] ?? 99)
    })
    return hasOverdue ? 'red' : null
  }
  if (col === 'interview' && jobs.length > 0) return 'accent'
  return null
}

export function getColumnLabel(col: BoardColumn, count: number): string {
  const labels: Record<BoardColumn, string> = {
    discover: `${count} new`,
    shortlist: `${count} prepping`,
    referral: `${count} job${count !== 1 ? 's' : ''}`,
    applied: `${count} in flight`,
    interview: `${count} active`,
  }
  return labels[col]
}

// Keep RawJob signature for callers that still use the full type
export { type RawJob }

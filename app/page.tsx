export const dynamic = 'force-dynamic'

import { readJobs } from '@/lib/data'
import { groupByColumn, buildGoals, buildStripItems } from '@/lib/board'
import { slimJob } from '@/lib/slim'
import Board from '@/components/Board'

const DISCOVER_LIMIT = 50

export default async function HomePage() {
  const { active_jobs } = await readJobs()
  const slim = active_jobs.map(slimJob)
  const columns = groupByColumn(slim)
  const goals = buildGoals(slim)
  const stripItems = buildStripItems(slim)

  // Cap discover column for initial render to keep payload small
  const discoverTotal = columns.discover.length
  columns.discover = columns.discover.slice(0, DISCOVER_LIMIT)

  return (
    <Board
      columns={columns}
      goals={goals}
      stripItems={stripItems}
      discoverTotal={discoverTotal}
    />
  )
}

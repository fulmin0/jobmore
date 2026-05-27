import fs from 'fs/promises'
import path from 'path'
import type { JobsData, RawJob } from './types'

const DATA_PATH = path.join(process.cwd(), 'data', 'jobs_found.json')

export async function readJobs(): Promise<JobsData> {
  const raw = await fs.readFile(DATA_PATH, 'utf-8')
  return JSON.parse(raw) as JobsData
}

export async function writeJobs(data: JobsData): Promise<void> {
  await fs.writeFile(DATA_PATH, JSON.stringify(data, null, 2), 'utf-8')
}

export async function patchJob(id: number, patch: Partial<RawJob>): Promise<RawJob | null> {
  const data = await readJobs()
  const idx = data.active_jobs.findIndex(j => j.id === id)
  if (idx === -1) return null
  data.active_jobs[idx] = { ...data.active_jobs[idx], ...patch }
  await writeJobs(data)
  return data.active_jobs[idx]
}

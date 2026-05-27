import type { RawJob } from './types'

export interface SlimJob {
  id: number
  title: string
  company: string
  location: string
  score: number
  job_url: string
  date_found: string
  pipeline: RawJob['pipeline']
  feedback: RawJob['feedback']
}

export function slimJob(job: RawJob): SlimJob {
  return {
    id: job.id,
    title: job.title,
    company: job.company,
    location: job.location,
    score: job.score,
    job_url: job.job_url,
    date_found: job.date_found,
    pipeline: job.pipeline,
    feedback: job.feedback,
  }
}

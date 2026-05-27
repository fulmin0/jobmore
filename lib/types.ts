export type PipelineStatus =
  | 'want_to_apply'
  | 'content_ready'
  | 'referral_found'
  | 'referral_submitted'
  | 'applied'
  | 'recruiter_screen'
  | 'interview'
  | 'offer'
  | 'rejected'
  | 'withdrawn'

export type BoardColumn = 'discover' | 'shortlist' | 'referral' | 'applied' | 'interview'

export interface RawJob {
  id: number
  title: string
  company: string
  location: string
  description: string
  job_url: string
  date_posted: string | null
  site: string
  salary_source: string | null
  sources: Array<{ platform: string; url: string }>
  score: number
  score_breakdown: {
    title_match: number
    role_scope: number
    company_signal: number
    domain_overlap: number
    location: number
    yoe_required: number | null
    yoe_fit: number
    salary_adjustment: number
    age_decay: number
    feedback_adj: number
    total: number
  }
  score_label: string
  date_found: string
  action: string
  detail_file?: string
  pipeline?: {
    status: PipelineStatus
    date_added: string
    date_updated: string
    notes: string
    history: Array<{ status: string; date: string }>
  }
  feedback?: {
    rating: 'relevant' | 'maybe' | 'not_relevant'
    notes: string
    date_rated: string
    score_flags: string[]
  }
}

export interface JobsData {
  active_jobs: RawJob[]
  next_id: number
}

export interface Goal {
  label: string
  done: number
  target: number
  tone?: 'red' | 'green'
}

export interface StripItem {
  id: number
  label: string
  overdue: boolean
}

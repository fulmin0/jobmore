import { NextResponse } from 'next/server'
import { readJobs } from '@/lib/data'

export async function GET() {
  try {
    const data = await readJobs()
    return NextResponse.json(data.active_jobs)
  } catch {
    return NextResponse.json({ error: 'Failed to read jobs' }, { status: 500 })
  }
}

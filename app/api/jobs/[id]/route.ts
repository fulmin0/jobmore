import { NextResponse } from 'next/server'
import { readJobs, writeJobs } from '@/lib/data'
import type { PipelineStatus } from '@/lib/types'

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: idStr } = await params
    const id = parseInt(idStr, 10)
    const body = await request.json() as {
      pipelineStatus?: PipelineStatus
      notes?: string
    }

    const data = await readJobs()
    const idx = data.active_jobs.findIndex(j => j.id === id)
    if (idx === -1) return NextResponse.json({ error: 'Not found' }, { status: 404 })

    const job = data.active_jobs[idx]
    const today = new Date().toISOString().split('T')[0]

    if (body.pipelineStatus !== undefined) {
      if (!job.pipeline) {
        job.pipeline = {
          status: body.pipelineStatus,
          date_added: today,
          date_updated: today,
          notes: '',
          history: [{ status: body.pipelineStatus, date: today }],
        }
      } else {
        job.pipeline.history.push({ status: body.pipelineStatus, date: today })
        job.pipeline.status = body.pipelineStatus
        job.pipeline.date_updated = today
      }
    }

    if (body.notes !== undefined && job.pipeline) {
      job.pipeline.notes = body.notes
      job.pipeline.date_updated = today
    }

    await writeJobs(data)
    return NextResponse.json(job)
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: idStr } = await params
    const id = parseInt(idStr, 10)

    const data = await readJobs()
    const before = data.active_jobs.length
    data.active_jobs = data.active_jobs.filter(j => j.id !== id)
    if (data.active_jobs.length === before) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 })
    }

    await writeJobs(data)
    return NextResponse.json({ ok: true })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}

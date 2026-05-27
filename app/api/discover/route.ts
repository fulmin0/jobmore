import { NextResponse } from 'next/server'
import { exec } from 'child_process'
import { promisify } from 'util'

const execAsync = promisify(exec)

export async function POST() {
  try {
    const venv = '/Users/fulmin/Develop/jobmore/venv/bin/activate'
    const cwd = '/Users/fulmin/Develop/jobmore'
    const { stdout, stderr } = await execAsync(
      `source "${venv}" && python3 scripts/discover.py`,
      { shell: '/bin/bash', cwd, timeout: 120000 }
    )
    return NextResponse.json({ ok: true, output: stdout, warnings: stderr || null })
  } catch (err) {
    const error = err as { message: string; stderr?: string; stdout?: string }
    return NextResponse.json(
      { ok: false, error: error.message, stderr: error.stderr ?? null },
      { status: 500 }
    )
  }
}

import { execFileSync } from 'node:child_process'
import { existsSync, mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'

const root = process.cwd()
const cp6Marker = resolve(root, 'supabase/migrations/20260904111157_erp_v2_6_20_cp6_laundry_qc_fg_authoritative.sql')
const cp6Predecessor = '6d4cda118f5d28d1f039cc0ecf318d0866f55c2c'

function run(command, args, cwd = root, stdio = 'pipe') {
  return execFileSync(command, args, { cwd, encoding: 'utf8', stdio })
}

if (!existsSync(cp6Marker)) {
  run(process.execPath, ['scripts/check-backend-ownership-v3.mjs'], root, 'inherit')
  process.exit(0)
}

try {
  run('git', ['cat-file', '-e', `${cp6Predecessor}^{commit}`])
} catch {
  throw new Error(`CP6 predecessor ${cp6Predecessor} is unavailable. Fetch full history before claiming backend ownership PASS.`)
}

const temporaryRoot = mkdtempSync(join(tmpdir(), 'erp-cp6-predecessor-'))
const worktree = join(temporaryRoot, 'checkout')
let worktreeRegistered = false
try {
  run('git', ['worktree', 'add', '--detach', worktree, cp6Predecessor])
  worktreeRegistered = true
  run(process.execPath, ['scripts/check-backend-ownership-v3.mjs'], worktree, 'inherit')
  console.log(`Predecessor backend ownership passed at exact CP5 base ${cp6Predecessor}; current CP6 overlays remain owned by check:cp6.`)
} finally {
  if (worktreeRegistered) {
    try { run('git', ['worktree', 'remove', '--force', worktree]) } catch { /* cleanup fallback below */ }
  }
  rmSync(temporaryRoot, { recursive: true, force: true })
}

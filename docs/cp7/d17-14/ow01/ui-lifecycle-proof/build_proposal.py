from pathlib import Path
import difflib
import hashlib
import json
import re

repo = Path('/workspace/scratch/9442228ed2dc/erp-d1714')
out = Path('/workspace/scratch/9442228ed2dc/ow01-proposals/ui/lifecycle')
target = 'src/ConnectedRemindersWa.dom.test.tsx'
base = out / 'base' / Path(target).name
if not base.exists():
    base.write_text((repo / target).read_text())
original = base.read_text()
helper = r'''

// OW01_UI_10..11: PAUSE_RESUME_UI_EXPECTED.md was written before execution.
// Each case has a separate source subject and row identity, never a synthetic
// click on an unavailable control. Keep all twenty review fields unchanged.
function accessoryLifecycleReply(states: { caseId: string; wa: ReturnType<typeof waState> }[]) {
  const reply = accessoryAlertsReply()
  reply.rows = states.map(({ caseId, wa }, n) => {
    const d = accessoryNeedDetail({ target_key: `${id(1001 + n)}:${id(1101 + n)}` })
    return row(1201 + n, 'ACCESSORY_NEED', `${ACCESSORY_TITLE} · ${caseId}`, d, {
      subject_key: `ACCESSORY_NEED:${d.target_key}:${d.category_key}`, wa,
    })
  })
  return reply
}
const accessoryLifecycleRow = (caseId: string) => field<HTMLElement>(`[aria-label="Pengingat sistem ${ACCESSORY_TITLE} · ${caseId}"]`)
'''
marker = "\nconst accessRefusal = (status: number)"
if original.count(marker) != 1:
    raise RuntimeError('The lifecycle fixture insertion anchor changed.')
proposed = original.replace(marker, helper + marker)

tests = r'''

  it('OW01_UI_10_PAUSED_FIRST_NOTICE explains pauses in both waiting states and refreshes the same first notice without a resend claim', async () => {
    const reasons = [
      { reason: 'WA_OFF', label: 'WA: ditahan, WhatsApp mati' },
      { reason: 'PHONE_MISSING', label: 'WA: ditahan, nomor belum diisi' },
      { reason: 'KEY_MISSING', label: 'WA: ditahan, kunci belum ada' },
      { reason: 'NOT_CONFIGURED', label: 'WA: ditahan, belum diatur' },
      { reason: 'KIND_OFF', label: 'WA: ditahan, jenis dimatikan' },
    ]
    const cases = ['PENDING', 'HELD_QUIET'].flatMap(state => reasons.map(({ reason, label }) => ({
      caseId: `${state}_${reason}`, state, label, wa: waState(state, { reason }),
    })))
    const reply = accessoryLifecycleReply(cases), before = structuredClone(reply.rows)
    const fake = server({ alertsData: reply })
    expect(() => parseSystemAlerts(reply, { owner: true })).not.toThrow()
    await mount(); await tab('Pengingat sistem')
    expect(panel(ACCESSORY_KIND_LABEL).querySelectorAll('li.csys-row')).toHaveLength(10)
    for (const c of cases) {
      const item = accessoryLifecycleRow(c.caseId), chip = item.querySelector('.csys-wa')
      expect(chip?.textContent, c.caseId).toBe(c.label)
      expect(chip?.classList.contains('off'), c.caseId).toBe(true)
      expect(item.textContent, c.caseId).toContain('jumlah tambahan belum diketahui')
      expect(item.textContent, c.caseId).toContain('kebutuhan BOM (perkiraan) 186 PCS')
      expect(item.textContent, c.caseId).not.toMatch(/kirim ulang|WA: jam tenang|perlu dibeli|tambahan 0/)
    }

    // The server later reports that the pause is no longer applicable. Refresh
    // the same public rows; no fresh episode, repeat or browser mutation occurs.
    for (const item of reply.rows) item.wa = { ...(item.wa as ReturnType<typeof waState>), reason: null }
    await click('Muat ulang pengingat sistem')
    for (const [n, c] of cases.entries()) {
      expect(reply.rows[n]).toMatchObject({ id: before[n].id, subject_key: before[n].subject_key, episode: 1, wa: { round: 0 } })
      const chip = accessoryLifecycleRow(c.caseId).querySelector('.csys-wa')
      expect(chip?.textContent, c.caseId).toBe(c.state === 'HELD_QUIET' ? 'WA: jam tenang' : 'WA: menunggu')
      expect(chip?.classList.contains('wait'), c.caseId).toBe(true)
      expect(accessoryLifecycleRow(c.caseId).textContent, c.caseId).not.toMatch(/WA: ditahan|kirim ulang/)
    }
    expect(calls(fake, 'erp_cp7_get_alerts_v1')).toHaveLength(2)
    expect(fake.calls.some(([name]) => /erp_cp7_(save|set|send|resolve)_/.test(name))).toBe(false)
  })

  it('OW01_UI_11_REPEAT_WAIT_AND_DELIVERY_STATES distinguishes paused repeats, actual retries and authoritative delivery states', async () => {
    const cases = [
      ...['PENDING', 'HELD_QUIET'].flatMap(state => [
        { caseId: `${state}_REPEAT_OFF`, wa: waState(state, { round: 1, reason: 'REPEAT_OFF' }), label: 'WA: pengulangan dimatikan', tone: 'off' },
        { caseId: `${state}_REPEAT_NOT_DUE`, wa: waState(state, { round: 1, reason: 'REPEAT_NOT_DUE' }), label: 'WA: menunggu jadwal pengulangan', tone: 'wait' },
      ]),
      { caseId: 'FIRST_PENDING', wa: waState('PENDING'), label: 'WA: menunggu', tone: 'wait' },
      { caseId: 'SOURCE_RECHECK_UNPROVEN', wa: waState('PENDING', { reason: 'RECHECK_UNKNOWN' }), label: 'WA: menunggu', tone: 'wait' },
      { caseId: 'QUIET_CURRENT', wa: waState('HELD_QUIET'), label: 'WA: jam tenang', tone: 'wait' },
      ...['PROVIDER_REFUSED', 'TRANSPORT_FAILED', 'OWNER_NOT_DELIVERED'].map(reason => ({
        caseId: `ACTUAL_RETRY_${reason}`, wa: waState('PENDING', { reason }), label: 'WA: menunggu kirim ulang', tone: 'wait',
      })),
      { caseId: 'ORDINARY_REPEAT', wa: waState('PENDING', { round: 1 }), label: 'WA: menunggu kirim ulang', tone: 'wait' },
      { caseId: 'ACCEPTED_FIRST', wa: waState('ACCEPTED', { reason: 'KIND_OFF', dispatch_id: 101, dispatch_status: 'PROVIDER_ACCEPTED', settled_at: NOW }), label: 'WA: terkirim', tone: 'ok' },
      { caseId: 'ACCEPTED_REPEAT', wa: waState('ACCEPTED', { round: 1, reason: 'REPEAT_OFF', dispatch_id: 102, dispatch_status: 'PROVIDER_ACCEPTED', settled_at: NOW }), label: 'WA: terkirim (ulangan ke-1)', tone: 'ok' },
      { caseId: 'UNKNOWN_REMAINS_UNKNOWN', wa: waState('UNKNOWN', { reason: 'WA_OFF', dispatch_id: 103, dispatch_status: 'UNKNOWN', settled_at: NOW }), label: 'WA: belum pasti', tone: 'bad' },
      { caseId: 'DISPATCHED_REMAINS_IN_FLIGHT', wa: waState('DISPATCHED', { reason: 'KIND_OFF', dispatch_id: 104, dispatch_status: 'QUEUED' }), label: 'WA: sedang dikirim', tone: 'wait' },
      { caseId: 'LEGACY_TERMINAL_KIND_OFF', wa: waState('KIND_OFF', { reason: 'KIND_OFF', settled_at: NOW }), label: 'WA: jenis dimatikan', tone: 'off' },
      { caseId: 'LEGACY_TERMINAL_DISABLED', wa: waState('DISABLED', { reason: 'WA_OFF', settled_at: NOW }), label: 'WA: tidak dikirim, WhatsApp mati', tone: 'off' },
    ]
    const reply = accessoryLifecycleReply(cases), before = structuredClone(reply)
    const fake = server({ alertsData: reply })
    expect(() => parseSystemAlerts(reply, { owner: true })).not.toThrow()
    await mount(); await tab('Pengingat sistem')
    expect(panel(ACCESSORY_KIND_LABEL).querySelectorAll('li.csys-row')).toHaveLength(cases.length)
    for (const c of cases) {
      const item = accessoryLifecycleRow(c.caseId), chip = item.querySelector('.csys-wa')
      expect(chip?.textContent, c.caseId).toBe(c.label)
      expect(chip?.classList.contains(c.tone), c.caseId).toBe(true)
      expect(item.textContent, c.caseId).toContain('jumlah tambahan belum diketahui')
      expect(item.textContent, c.caseId).not.toMatch(/perlu dibeli|tambahan 0/)
    }
    expect(reply).toEqual(before)
    expect(fake.calls.some(([name]) => /erp_cp7_(save|set|send|resolve)_/.test(name))).toBe(false)
  })
'''
marker = "\n  it('shows the server refusal in words when the connection read is refused'"
if proposed.count(marker) != 1:
    raise RuntimeError('The lifecycle test insertion anchor changed.')
proposed = proposed.replace(marker, tests + marker)

proposed_path = out / 'proposed' / Path(target).name
proposed_path.write_text(proposed)
expect_name = 'docs/cp7/d17-14/ow01/PAUSE_RESUME_UI_EXPECTED.md'
expect_doc = (out / 'PAUSE_RESUME_UI_EXPECTED.md').read_text()
patch = ''.join(difflib.unified_diff(original.splitlines(True), proposed.splitlines(True), fromfile='a/' + target, tofile='b/' + target))
patch += ''.join(difflib.unified_diff([], expect_doc.splitlines(True), fromfile='/dev/null', tofile='b/' + expect_name))
(out / 'paused-notice-dom.patch').write_text(patch)

isolated = out / 'isolated'
for child in (repo / 'src').iterdir():
    dest = isolated / 'src' / child.name
    if child.name == Path(target).name:
        dest.write_text(proposed)
    elif not dest.exists() and not dest.is_symlink():
        dest.symlink_to(child, target_is_directory=child.is_dir())
for name in ('tests', 'node_modules'):
    dest = isolated / name
    if not dest.exists() and not dest.is_symlink():
        dest.symlink_to(repo / name, target_is_directory=True)
(isolated / 'vitest.config.mjs').write_text(f"""import {{ defineConfig }} from '{repo}/node_modules/vitest/dist/config.js'
import react from '{repo}/node_modules/@vitejs/plugin-react/dist/index.js'
export default defineConfig({{
  root: '{isolated}', cacheDir: '{isolated}/cache', plugins: [react()],
  server: {{ fs: {{ allow: ['{repo}', '{isolated}'] }} }},
  test: {{ include: ['src/ConnectedRemindersWa.dom.test.tsx'], fileParallelism: false, maxWorkers: 1, cache: false }},
}})
""")
(isolated / 'tsconfig.json').write_text(json.dumps({
    'extends': str(repo / 'tsconfig.app.json'),
    'compilerOptions': {'noEmit': True, 'incremental': False},
    'include': ['src/ConnectedRemindersWa.dom.test.tsx', str(repo / 'src/vite-env.d.ts')],
}, indent=2) + '\n')

old_titles = re.findall(r"^  it(?:\.each\([^\n]*)?\('[^\n]*", original, re.M)
new_titles = re.findall(r"^  it(?:\.each\([^\n]*)?\('[^\n]*", proposed, re.M)
result = {
    'base_file_sha256': hashlib.sha256(original.encode()).hexdigest(),
    'proposed_file_sha256': hashlib.sha256(proposed.encode()).hexdigest(),
    'expected_sha256': hashlib.sha256(expect_doc.encode()).hexdigest(),
    'old_direct_declarations_retained': all(t in new_titles for t in old_titles),
    'added_direct_declarations': [t for t in new_titles if t not in old_titles],
    'scope': 'Test and expected-document proposal only; no active repository writes.',
}
(out / 'proposal-manifest.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))

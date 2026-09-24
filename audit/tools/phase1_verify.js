export const meta = {
  name: 'cp6-blind-phase1-verify',
  description: 'Two-lens adversarial refutation of P0-P2 findings from the blind phase-1 readers',
  phases: [{ title: 'Verify', detail: 'code lens + contract lens per finding' }],
}
const SP = '/tmp/claude-0/-home-user--erp-garment-ux/2a0eb6c3-bb79-5f14-b9f8-6487e74e773f/scratchpad'
const M = SP + '/pack/kontrak/ERP_V3_2_Master_Pulih_20260923.md'
const P = SP + '/pack/kontrak/ERP_V3_2_Perubahan_Pulih_20260923.md'
const A = SP + '/pack/kontrak/ERP_ADDENDUM_BUSINESS_REPORT_CP7_2026-09-18.md'
const RULES = `
You are one agent of an INDEPENDENT, BLIND audit of the CP6 ERP Garment candidate (frozen commit 9add57e). Paths (read-only): candidate ${SP}/cand, baseline ${SP}/base, harness ${SP}/harness, pinned CI candidate ${SP}/cand25fa. CONTRACT (only source of truth): ${M}, ${P}, ${A} (Addendum only for CP6/CP7 boundary). Background only: ${SP}/pack/latar/ERP_GARMENT_MASTER_CONTEXT_2026-09-06.md. Reader notes: ${SP}/out/*.md. Gate-run facts from the auditor's own reruns on 9add57e: ${SP}/out/gate_runs_summary.txt.
HARD LIMITS: never modify files under cand/base/harness/cand25fa or the repo; never git push/checkout/reset; never dispatch workflows or call GitHub/Supabase/Cloudflare tools; never run SQL against a database. BLIND: never read docs/ in any worktree, never read commit messages (git log only with --format='%H %ad'), never read GitHub run logs of other auditors. Docstrings/comments/assertions in scripts and SQL are writer claims, not oracle. Quote contract with file:line.
`
const VERDICT = { type: 'object', properties: {
  refuted: { type: 'boolean' }, verdict: { type: 'string', enum: ['CONFIRMED', 'REFUTED', 'UNVERIFIED'] },
  reasoning: { type: 'string' }, corrected_severity: { type: 'string', enum: ['P0', 'P1', 'P2', 'P3', 'INFO'] },
  corrected_claim: { type: 'string' }, evidence_checked: { type: 'array', items: { type: 'string' } },
}, required: ['refuted', 'verdict', 'reasoning', 'corrected_severity', 'evidence_checked'] }
const LENSES = [
  ['code', 'Lens CODE: re-open every cited file:line yourself and try to REFUTE the technical claim (does the code really do what the finding says? is there a guard elsewhere that prevents it? is the cited line misread?). Default to refuted=true unless the cited evidence, re-read by you, supports the claim.'],
  ['contract', 'Lens CONTRACT: re-open the cited contract lines yourself and try to REFUTE that the contract actually requires or forbids what the finding says (is the quote accurate and still in force, e.g. not superseded by owner decisions after R4 at Master 1054-1090? is the severity justified by the contract wording? is it CP6 scope and not CP7 per R1.4 / Addendum?). Default to refuted=true unless the contract, re-read by you, supports the claim.'],
]
const findings = (args && args.findings) || []
phase('Verify')
log(`Verifying ${findings.length} findings with 2 lenses each`)
const verified = await pipeline(findings,
  f => parallel(LENSES.map(([name, lens]) => () =>
    agent(RULES + `\nADVERSARIAL VERIFICATION. A previous reader (${f.from}; its notes are in ${SP}/out/) reported this finding:\n` + JSON.stringify(f, null, 2) + '\n\n' + lens + '\nReturn the verdict; corrected_claim must restate the claim precisely if it survives (possibly narrowed).',
      { label: `verify:${name}:${f.id}`, phase: 'Verify', schema: VERDICT, effort: 'high' })))
    .then(vs => ({ finding: f, votes: vs.filter(Boolean) }))
)
const out = verified.filter(Boolean).map(({ finding, votes }) => {
  const confirmed = votes.filter(v => v.verdict === 'CONFIRMED').length
  const refuted = votes.filter(v => v.verdict === 'REFUTED').length
  const status = votes.length === 2 && confirmed === 2 ? 'CONFIRMED' : refuted === 2 ? 'REFUTED' : 'UNVERIFIED'
  return { ...finding, verification: status, votes }
})
log(`Verify done: ${out.filter(o => o.verification === 'CONFIRMED').length} confirmed, ${out.filter(o => o.verification === 'REFUTED').length} refuted, ${out.filter(o => o.verification === 'UNVERIFIED').length} unverified`)
return { verified_findings: out }

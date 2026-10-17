# r3 writer handoff (living checkpoint)

Owner 17 Okt: "kalo terlalu banyak bikinnya satu satu biar ga kepotong limit kayak tadi, saat mendekati limit habis cari
check poin terdekat untuk forward ke writer sol". This file is that checkpoint. It is updated with every r3 commit on
`claude/r3-fixes-20261017`; the last commit that touches it is the checkpoint to continue from.

## Rules that stay in force

- Owner reports: plain everyday Indonesian, first sentence says what is done and what is not (CLAUDE.md).
- Follow `docs/ERP_BEST_PRACTICES.md` and its checklist; new general audit lessons go there with their finding IDs.
- Never mutate: main, Cloudflare deployment, Supabase hosted Enteng (`siimvrusnzxexizpyoib`), legacy ERP-Garment
  (`vlxdhpkjeevubjxexnfo`, read-only), production. `production_go:false`; D13-9a (the writer does not touch hosted or Drive).
- Do not loosen old oracles/guards to get green; keep failed logs and wrong fixtures. Do not reopen approved decisions.
- No production dump in the repo, public artifacts or logs. No paid services. No messages to other people. No PR.

## Mandate (r3)

Fix all r2 audit findings and implement owner decisions D16-1..D16-5 (verbatim in `docs/cp7/OWNER_DECISIONS_20261008.md`),
qualify on one commit, prepare the retest package for Fable/Astra/Sol, then a short owner report. Fable's retest oracle for
D16-1 (1-5) is in `audit/fable_cp17_r2/OWNER_DECISION_TO_AUDITOR_20261016_UNHIDE.md` (branch
`audit/fable-cp1-7-r2-2e9d6a46-20261016`).

## Done (committed and pushed)

| Item | Where |
|---|---|
| R3-01 auto-PO number past 999, R3-02 PO reopen counts only active FG use | `cp7_r3_cases.py` |
| R3-09 mandor rate old/new (D16-2..D16-4) | `cp7_r3_rate_cases.py`; CP17 run 39004765824 175/175 PASS at cf08a4d0 |
| D16-5 "Laporan & Tutup Buku" with the "Tutup Buku" tab, history, old link redirected | `cp7_r3_period_cases.py`, `src/ConnectedFinanceReportPage.tsx`, `src/App.tsx` |
| D16-1 Enteng build test: the CP17 browser cases run a second time on the Enteng-mode build (`_ENTENG` ids) | `scripts/cp6_auditor_browser_host.mjs` (`AUDITOR_UI_MODE=ENTENG`), workflow pins the Enteng host to loopback |
| D16-1 new screens on real data: Reminder, Pengaturan ERP, Audit Trail, Riwayat Pelanggan, Ringkasan Gudang | `cp7_r3_{reminders,settings,audit,history,warehouse}_cases.py` + browser + `src/Connected*Page.tsx` |
| R3-04 attendance HPP pool on HPP & Rekalkulasi (D16-1; Sol KNOWN-R2-POOL-UI, ASTRA-C17-07) | `scripts/cp7-src/hpp-pool/pool.sql`, `cp7_r3_hpp_pool_cases.py`, `src/AttendanceHppPoolPanel.tsx` |
| `screenActivation`: no hidden menu in Enteng (47 menus; dashboard is NOTICE) | `src/screenActivation.test.ts` passes |
| Fable oracle 3 chains (sewing -> close; FG -> AR zero on a phone; D14-2, D14-3/D15-1, D15-5 guards) | `cp7_r3_chain_cases.py`, `cp7_r3_chain_browser.mjs` (registered right after R2-07) |
| R3-06/07 test tools (Laundry alert read without waiting; CI receipt reads every page), R3-08 CP6 workflow successor map | commit 0e9e6fbc; `docs/cp7/audit-candidate/cp1-7-r3-20261017/R3_08_CP6_WORKFLOW_SUCCESSORS.md` |
| R3-05 (FABLE-016 remainder): QC & Final SKU and accessory note -> payroll browser cases | `cp7_r3_qc_note_cases.py`, `cp7_r3_qc_note_browser.mjs` |

Declaration `docs/cp7/cp17/CP17_FIXES.json`: 321 cases (native 153, races 34, http 24, browser 55, browser_enteng 55);
private role stack 49 (`cp7_f03_full_probe.py`, both manifests).

## Not done yet (in this order)

1. CI on the current head: dispatch `claude-cp17-fixes.yml`, `cp7-p13-period.yml`, `cp7-f03-p13-regression.yml`,
   `claude-p13-finance.yml` and the F03 full workflow on `claude/r3-fixes-20261017`; fix real failures (the 5 new screens'
   CP17 cases, the 17 HPP pool cases, the 3 R3-05 and the 3 chain browser cases have never run on the full stack yet; see each module's docstring and the
   risky selectors named there: QC search box `nav.clq-tabs input`, `.clq-impact`, `.cpay-net`).
2. Docs: r3 notes for D16-5, the D16-1 screens and the Enteng build go into the r3 package (its SCREEN_MAP lists
   "Laporan & Tutup Buku" with the Tutup Buku tab; older packages' SCREEN_MAP stay as they were). Install-time checks are
   in `docs/cp7/cp17/R3_INSTALL_TIME_CHECKS.md` (run at install, never on hosted now).
3. Qualify r3 on one commit (fast-forward `claude/new-session-deapao`, qualify, CI receipt, package + handoffs for
   Fable/Astra/Sol), then the owner report.

Held, not part of r3: CP7C and FABLE-012. Add to the CP7C revoke batch: the CP4 public pool wrappers
`public.erp_{preview,create,activate,cancel}_attendance_hpp_pool_v1` (still executable by authenticated; they skip the
new facade's closed-books refusal, review token and request table; `cp7_hpp_pool_bundle.verify` reports them).

## How to check locally

- Types and catalog: `npx tsc -p tsconfig.app.json --noEmit`; `node scripts/check-access-catalog.mjs`;
  `node scripts/check-source-ownership.mjs`; `node scripts/check-css-ownership.mjs`.
- Screen tests: `npx vitest run --dir src <files>` (cp7 family tests need a non-root native PostgreSQL; they fail in a root
  sandbox for that reason only).
- SQL: `python3 scripts/cp7_plpgsql_compile_check.py <file.sql>` (env `PGCHECK_DSN` or `PGCHECK_DB`) and
  `python3 scripts/cp7_plpgsql_clash_check.py <file.sql>`.
- Declaration must equal `cp7_cp17_fix_cases` (CONTRACT, EXPECTED, REQUIRED, IDS, FUNCTIONS); the CP17 probe refuses
  otherwise. Role stack must equal both manifests.

## Checkpoint log

| Commit subject | State after it |
|---|---|
| feat(r3): Ringkasan Gudang on real data (D16-1) | 5 of 6 D16-1 screens in; no hidden Enteng menu; CI not yet run on these 5 |
| test(r3): R3-05 QC and accessory-note browser cases | 296 declared cases; CI dispatched at 26a107d3 (CP17 39019699925, F03 full 39019701257, F03-P13 39019702513, P13 finance 39019703895, P13 period 39019705128) |
| test(r3): Fable oracle 3 screen chains | 302 declared cases; the chain cases are not in the 26a107d3 runs. CP17 39018740764 and P13 period 39018742406 at 1dace64e both green (Enteng-build browser group included) |
| feat(r3): attendance HPP pool screen (R3-04, D16-1) | all six D16-1 screens in; 321 declared cases, role stack 49; CI not yet run on it |

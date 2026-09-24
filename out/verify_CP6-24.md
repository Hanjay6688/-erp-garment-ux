# Verify CP6-24: close_accounting_through not idempotent for same date (race -> 2 filings)

## Claim
Two real concurrent owner/admin sessions calling `erp.close_accounting_through(D, reason)` (via
`erp_close_accounting_through_v1`) for the same date D, with preflight READY, both succeed; the
only date guard blocks an *earlier* date, not an equal one; filings are immutable, so
`erp.accounting_close_filings_v1` ends up with 2 rows for `closed_through=D` that can never be
merged/removed. Claimed oracle: Master 3816-3819 (Idempotent/atomic replay) + S06/close family
Master 1057-1065. Proposed P2.

## Refutation attempts

### A. CODE

1. **Race and guard reproduced exactly as described.**
   `supabase/dev/cp6_aw_t1_family.sql` `erp.close_accounting_through` (~line 618-660): locks
   `accounting_period_control` `for update`, then only checks
   `if v_old is not null and p_closed_through<v_old then raise ... reopen_accounting_through() ...`
   (line ~628-630). Equal date (`p_closed_through = v_old`) falls through, re-runs
   `period_readiness_v1`, no-op updates the control row, refreshes checkpoints, writes an
   `audit_logs` row, and unconditionally `insert`s a new `accounting_close_filings_v1` row
   (line ~653-659). Filings table has no unique constraint on `closed_through`
   (`supabase/dev/cp6_aw_t1_family.sql` lines 13-22) and is guarded immutable by
   `trg_guard_accounting_close_filing_immutable`/`..._truncate` (lines 907-910). Evidence file
   `auditor_xaudit5_36065517737.json` idx 8 confirms: `worker.ok=true`, `filings=2`,
   `closed_through="2026-09-24"`, `contention.kind=BLOCKED` (row-lock wait, not a real error) —
   matches the finding exactly.

2. **Not race-specific — a plain sequential double-close reproduces it too.** The guard logic is
   symmetric for concurrent and sequential calls: after the first commit, `v_old=D`; a second,
   later call with `p_closed_through=D` (no concurrency needed, e.g. a UI double-submit or client
   retry) hits the same `D<D` → false path and also inserts a second filing. This is **not new
   behavior added by the AW-T1 filings feature** — the byte-identical guard
   (`if v_old is not null and p_closed_through<v_old then raise ...`) already existed in the
   predecessor `erp.close_accounting_through` in
   `supabase/migrations/20260915031500_..._cp6_temporal_surface_closure.sql` line 2398-2416,
   before filings existed (it just wrote a second `audit_logs` row instead of a second filing).
   So this is long-standing, pre-existing "repeat-close is a no-op-ish re-affirmation" behavior,
   not a new race window introduced by this engine.

3. **No double GL/financial effect.** `close_accounting_through` does not post journal entries.
   The only per-material side effect is `erp.refresh_material_cost_checkpoint`
   (`supabase/migrations/20260921214120_..._transfer_integrity.sql` line 699+), which does
   `insert into erp.material_cost_checkpoints(...) on conflict(material_id) do update` (line
   ~129-131) — a keyed upsert, fully idempotent/re-entrant. Re-running it twice (once per close
   call) recomputes the same checkpoint value; it does not double-count or corrupt state.

4. **The duplicate filing is structurally invisible to the one identified downstream reader.**
   `erp.get_owner_financial_snapshot_v2` (lines ~792-798) selects the "current" filing via
   `where f.closed_through>=p_as_of and (f.previous_closed_through is null or
   f.previous_closed_through<p_as_of) order by f.filed_at desc,f.id desc limit 1`. For the
   degenerate duplicate (`previous_closed_through=D`, `closed_through=D`), the matching window is
   `p_as_of in (D, D]` — empty — so this filing can **never** be selected by that reader for any
   `p_as_of`. The `erp_close_accounting_through_v1` facade's own post-call reader
   (`where f.closed_through=p_closed_through order by filed_at desc,id desc limit 1`, line ~894)
   runs inside each caller's own transaction, so each of the two racing sessions correctly gets
   back its own filing (holder sees only filing #1 when it reads, since filing #2 doesn't exist
   yet in its transaction snapshot at that point; the worker, running after, sees filing #2, the
   latest by `filed_at`). No cross-session data leakage or wrong result observed or predicted.

5. **Multiple filings per `closed_through` are explicitly a designed pattern, not solely a bug
   artifact.** The code comment directly above the insert (line ~652) states: "Filed snapshot:
   never overwritten; later corrections are read from the engine as current-corrected values." A
   legitimate reopen -> correct -> re-close-to-the-same-date workflow (contract ERP-DEC01, lines
   1057-1065: post-close corrections on an open period follow invoice date and must be reflected
   consistently) is expected to produce a **second** filing for a date that was already closed
   before, with a genuinely different (earlier) `previous_closed_through`. The race merely
   produces a *degenerate* member of that same pattern (`previous_closed_through == closed_through`)
   that the guard doesn't special-case away. So "2 filings for the same closed_through" is not by
   itself off-contract; only the specific window-collapsing degenerate case is un-guarded.

6. **What the guard does NOT circumvent:** no unique index and no "no-op early return" exist for
   the equal-date case — confirmed absent by grep of the table DDL and the function body. This
   part of the finding is accurate.

### B. CONTRACT

1. **Cited oracle Master 3816-3819 does not literally apply here.** Read in full
   (`ERP_V3_2_Master_Pulih_20260923.md` lines 3816-3819): "**Idempotent dan fail-closed:**
   UUID/payload sama replay exact, UUID sama/payload beda ditolak. ... Sukses commit/refetch gagal
   berarti tersimpan menunggu sinkronisasi, bukan request baru." This is the codebase's
   client-idempotency-key pattern (a caller-supplied UUID, e.g.
   `erp.create_manual_bs_case_v2(p_payload jsonb, p_client_request_id uuid)`), used to dedupe
   retried writes by comparing UUID+payload. `erp.close_accounting_through(p_closed_through date,
   p_reason text)` and its facade `erp_close_accounting_through_v1` take **no idempotency-key
   parameter at all**. Applying the UUID-replay invariant to a command that was never designed
   with that parameter is an analogy, not a literal contract citation — the auditor's own
   "expected" field in the scenario (`M:3816/M:1057-1065: ... second is refused with the product
   message`) states this as if it were the contract's literal requirement, but no contract text
   anywhere mandates "close same date twice -> second call refused" or "exactly one filing per
   closed_through."

2. **Cited oracle "S06/close family Master 1057-1065" is a citation mismatch.** Lines 1057-1065 of
   the contract (checked directly, `sed -n '1050,1070p'`) are the ERP-DEC01/ACC-DEC02 "owner
   decisions after R4" section (open-period cost correction follows invoice date; manual retail
   price entry) — they say nothing about accounting close, filings, or session races. The actual
   S06 item lives at contract lines 5777 and 6049-6072 ("Tutup buku membutuhkan satu preflight dan
   pemeriksaan ulang seluruh blocker"). Reading S06 in full: its **entire** concern is preflight
   completeness — that `close_accounting_through` must aggregate all owner-mandated blockers
   (cost queue, attendance/payroll completeness, GRNI, stock/journal integrity) in one atomic
   recheck, not that repeat/concurrent closes must be deduplicated or refused. S06's own
   reproduction guidance even lists "dua sesi posting vs close" (two sessions posting vs. close)
   as a scenario to test, but in service of proving the preflight recheck is atomic and current —
   which the current code satisfies (the readiness check runs once, after the row lock, inside
   the same transaction as the state update, so no state can change between check and commit).
   Nothing in S06 discusses filing-count or once-only-close semantics.

3. **No contract text anywhere mentions "filing"** (`grep -n filing` on the whole contract file
   returns zero hits) or states "one filing per period" / "closed_through is unique" as an
   invariant. The append-only filings table and its immutability triggers are a candidate
   implementation choice (an audit-log pattern), not a documented contract requirement being
   violated by having >1 row per date.

4. Net: the contract *does* require close to be a correct, atomically-rechecked, owner/admin-gated
   operation (S06) — which it is, including under the race (readiness re-evaluated fresh under
   lock each time, `preflight_ready:true` in evidence). It does **not** contain a literal
   "idempotent-replay" or "one filing per closed_through" requirement that this behavior violates.
   The auditor's scenario file bakes its own expectation
   (`filings_exactly_one`, "second is refused") into the "expected" field and cites contract line
   numbers that, on inspection, don't say that.

## Residual doubts

- The degenerate duplicate filing (`previous_closed_through == closed_through`), while shown to be
  invisible to `get_owner_financial_snapshot_v2`, is still a permanent, immutable row in a table
  future reports/audits may query directly (e.g. `select * from accounting_close_filings_v1 where
  closed_through=D` without the window predicate) — a naive `count(*)` or "most recent filing per
  date" query without the `previous_closed_through<p_as_of` filter would see 2 rows / could pick
  the wrong one for date D specifically. This is a real, if narrow, latent-consumer/hygiene risk
  and a legitimate gap worth a guard or `on conflict` no-op, even absent a direct contract line.
- Did not exhaustively check every other reader of `accounting_close_filings_v1` across the repo
  (only the two in `cp6_aw_t1_family.sql`); a grep found no others, but a broader repo grep for
  `accounting_close_filings_v1` outside `supabase/` (e.g. frontend/report code) was not performed
  given the budget — low risk since the table is not exposed to `anon/authenticated` roles
  (`revoke all ... from public,anon,authenticated,service_role`, line 24) and is only reached
  through the two SECURITY DEFINER readers already examined.
- Did not verify whether `api.ordinary(cur)` in the scenario authenticates as a genuine
  owner/admin-mapped user in both racing sessions (as opposed to some test shortcut); the evidence
  (`holder_closed:true`, `worker.ok:true`, no `require_owner_admin` refusal) strongly implies both
  sessions passed the access gate, which is consistent with two real admins racing.

## Verdict: PARTIALLY_REFUTED

The **factual/code claim is CONFIRMED**: two racing (or even sequential) same-date closes both
succeed, the guard only blocks an earlier date, and 2 immutable filings for the same
`closed_through` result — exactly as described, verified at
`supabase/dev/cp6_aw_t1_family.sql` lines ~618-660 (guard + insert) and 907-910 (immutability
triggers).

The **severity/framing is REFUTED**: (1) the cited contract oracles (M:3816-3819, M:1057-1065)
do not actually mandate this behavior — 3816-3819 governs a different, UUID-keyed idempotency
pattern this function never used, and 1057-1065 is an unrelated ERP-DEC01 passage; the real S06
item (contract lines 5777/6049-6072) is about preflight completeness, which this code satisfies,
not about filing counts; (2) the equal-date guard gap is inherited unchanged from the
pre-AW-T1 predecessor function, not introduced by this change; (3) multiple filings per date are
an explicitly designed pattern for the reopen/correct/reclose workflow, and the race only produces
a degenerate, harmless member of it; (4) no double GL posting or checkpoint corruption occurs
(checkpoint refresh is an idempotent upsert); (5) the duplicate filing is provably unreachable by
the one identified downstream reader.

**Priority recommendation: downgrade P2 -> P3.** Worth fixing (add a no-op fast path or a partial
unique index disallowing `previous_closed_through=closed_through`, for hygiene and to protect
future naive consumers of the raw filings table), but it is not the contract-mandated
atomic/idempotent-replay violation the finding claims, and it causes no demonstrated financial or
reporting harm today.

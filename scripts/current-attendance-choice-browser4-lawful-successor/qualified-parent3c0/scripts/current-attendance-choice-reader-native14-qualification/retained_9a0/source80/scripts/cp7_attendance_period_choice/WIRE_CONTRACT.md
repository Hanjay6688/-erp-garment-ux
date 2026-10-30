# S03 wire contract v1 — frozen for separate panel implementation

The panel is a standalone addition; root owns mounting and shared menu changes.
Backend source lives only in this namespace over qualified vendor41c. Local
SQL controls pass15/15; actual installed Native/Auth/browser status is PREPARED.
No new database roles or changes to old frozen App/SQL are required.

All calls require current authenticated OWNER with `finance.hpp.view`. Save
also requires current `finance.hpp.manage`. Rights are checked after waits and
before request replay or commit. SQL error42501 means permission refusal; never
show a successful save or retain an actionable preview after that response.

| RPC | Named arguments | Result contract |
| --- | --- | --- |
| `erp_cp7_get_attendance_choice_v1` | `p_period_start`, `p_period_end`: canonical YYYY-MM-DD; `p_offset`: integer0..100000 default0; `p_limit`: integer1..50 default25 | `cp7.attendance-period-choice-workspace.v1` |
| `erp_cp7_preview_attendance_choice_v1` | `p_action`: exact enum below; `p_payload`: six-key object below | `cp7.attendance-period-choice.v1` |
| `erp_cp7_save_attendance_choice_v1` | same `p_action`; `p_payload`: same six keys plus exact `review_token`; `p_request`: client UUID retained for an uncertain response | `cp7.attendance-period-choice-command.v1` |

Every preview payload contains **all six keys**. Unused values must be JSON
null. Additional keys, malformed dates, null action, loose casing, whitespace
action variants and missing keys refuse. Period spans are at most366days.

```json
{
  "period_start": "2026-10-01",
  "period_end": "2026-10-07",
  "choice": "CARRY",
  "output_start": null,
  "output_end": null,
  "reason": "Alasan Owner yang jelas, 5 sampai 1000 karakter"
}
```

| Action | Choice | Output dates | Required current state |
| --- | --- | --- | --- |
| `CHOOSE` | `CARRY` or `EXPENSE` | both null | No current choice; exact source has positive normal-Mandor approved attendance and zero eligible sewing |
| `CORRECT` | `CARRY` or `EXPENSE` | both null | Current choice; cancel its active carry allocation first; appends owning inverse then replacement linked by `correction_of` |
| `REVERSE` | null | both null | Current choice; no active carry allocation; appends owning inverse |
| `ALLOCATE` | null | canonical strictly later exact period | Current CARRY without active allocation; later eligible Native output and lawful economic/book dates |
| `CANCEL_ALLOCATION` | null | both null | Current CARRY with its active carried Native pool; owning Native cancellation plus immutable private inverse |

Workspace returns `period_start/end`, `amount_cents` (string or null),
`source_binding` (SHA64 or null), `original_period_sewing_qty` (string or null),
`source_problem` (explicit refusal text or null), `closed_through` (date or null),
`current_choice` (`decision_id`, `choice`, `reason`, `journal_id`) or null,
`current_allocation` (`allocation_id`, `pool_id`, `output_start/end`) or null,
`can_manage` boolean, `business_DML:false`. History is bounded newest-first by
recorded timestamp and UUID: `history`, `history_total` exact string, `offset`,
`limit`, `next_offset` integer or null. History event enum is CHOOSE, REVERSE,
ALLOCATE, CANCEL_ALLOCATION, with immutable event/decision identifiers, actor,
reason and timestamp; applicable journal, correction, allocation, pool/output
fields accompany that event. A correction is two linked audit events.

Successful preview returns `action`, canonical `payload`, `amount` decimal
string, `amount_cents` integer string, `source_count` integer string,
`denominator_qty` integer string or null, `economic_date`, `book_date`,
`inverse_economic_date`, `inverse_book_date` (nullable dates), `decision_id`,
`allocation_id`, `pool_id` (nullable UUIDs), `source_binding`, `review_token`,
`expense_account` (`id`, `code`, `name`) or null, `can_apply:true`,
`business_DML:false`. It never returns the private raw source context. Refused
preview raises an explicit error; it does not fabricate zero figures or a
success-shaped blocked object. Zero eligible output for ALLOCATE leaves WIP
waiting; it does not create a placeholder pool.

Save adds only `review_token` to the exact reviewed payload. Its immutable
receipt contains `action`, `request_id`, source period, `decision_id`,
`event_id`, `amount_cents` string, nullable `pool_id`, `native_result`,
`inverse_journal_id`, dated WIP proof and `status:COMMITTED`. An exact UUID
replay returns that historical receipt after fresh authority checks. It is not
the current choice after subsequent corrections: reload workspace on success
or recovered response. A changed payload with the same UUID refuses.

| Refusal prefix | UI behavior |
| --- | --- |
| `CP7_S03_OWNER_REQUIRED`, `USER_INACTIVE`, `ACCESS_CHANGED`, SQL42501 | Clear actionable preview; show current permission refusal |
| `CP7_S03_STALE_REVIEW`, `SOURCE_CHANGED` | Keep typed reason/dates, retire preview and fetch current source; require a new explicit preview |
| `CP7_S03_PERIOD_CLOSED` | Show affected period and legitimate reopen requirement |
| `CP7_S03_EXPENSE_BEFORE_WIP_AVAILABLE`, `ALLOCATION_BEFORE_WIP_AVAILABLE`, `WIP_NEGATIVE_DATED` | Show that allocation/re-expense would precede source recognition/restoration; no backdating shortcut |
| `CP7_S03_LATER_OUTPUT_NOT_AVAILABLE`, `OUTPUT_EXISTS`, `NO_ELIGIBLE_COST` | Explain actual source/output state; no false zero or successful save |
| `CP7_S03_CANCEL_CARRY_FIRST`, `CURRENT_CARRY_REQUIRED`, `CHOICE_EXISTS`, `CHOICE_NOT_FOUND`, `ACTIVE_CARRY_ALLOCATION_REQUIRED` | Reload current choice/allocation and require its owning lifecycle |
| `CP7_S03_REQUEST_CHANGED` | Do not retry a modified action under the old request UUID |
| Native current-period, downstream HPP/cost, policy, source or journal error | Retain its explicit reason, retire actionable preview, no success message |

The panel must retire pending reads/previews/saves when source period, action,
choice, output dates, reason or parent blocked/access state changes. Late
results cannot publish/copy/save against a new state. Preserve uncertain save
UUID plus its exact action/payload for recovery; do not create a new request
while the old result is unknown. Treat exact cents as strings, using existing
decimal formatting; never calculate accounting values with floating point.
Draft inputs and previews are not posted business facts. Display both source
and separate output periods, actual economic/book/inverse dates and expense
account before confirmation. CARRY waiting has no allocation journal; PAID is
settlement, not new attendance cost. A source problem or parent blocked state
must leave no actionable save even if an older preview exists.

This contract provides no actual Auth/browser PASS or production acceptance.

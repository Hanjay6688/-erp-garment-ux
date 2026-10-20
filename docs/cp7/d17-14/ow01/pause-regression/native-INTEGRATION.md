Read-only proposal against base f412e61be645b974ecca27862501b8e5b6e0c2ab.
All files in this directory were prepared outside the active repository.

`native-module.patch` adds only `scripts/cp7_wa_accessory_cases.py`. Root is
the sole integrator. Before copying, it can inspect/check the add-file patch:

```bash
git -C /workspace/scratch/9442228ed2dc/erp-d1714 apply --check /workspace/scratch/9442228ed2dc/ow01-proposals/native/native-module.patch
```

`native54-identifiers.json` contains all 48 retained Native IDs, then the six
additions in order. The transport integrator owns the shared complete 77-case
manifest/integration patch: Native54, races9, HTTP5, browser9. Do not run a
partial declaration whose counts and function lists differ.

The main case module may import `NATIVE_IDS as ACCESSORY_NATIVE_IDS`, append
that list after the existing seven obligation IDs, then assemble closures as
follows (inside its existing `cases(cur,today)`):

```python
import sys
import cp7_wa_accessory_cases as accessory
old = list(zip(IDS['native'][:len(named)], named)) + obligation_cases(cur, today)
assert len(old) == 48
extra = accessory.cases(cur, today, sys.modules[__name__])
result = old + extra
assert len(result) == 54 and [key for key, _ in result] == IDS['native']
return result
```

The existing preflight count/manifest checks must run before cases. Keep the
old 65 IDs as unchanged group prefixes. WA has its own phase and count; F05's
default154 is unaffected. The proposed complete run command remains:

```bash
python scripts/cp7_wa_forward_probe.py
```

The integrator must also include `accessory_target_now` in both the bundle
capability list and the staged-reminder cases' exact `CAPABILITIES` tuple. The
new helper's actual signature is `(uuid,text,text,integer)`. No application
role may execute it directly, and no ERP DML grants are added for setup.

Helper API for the transport/browser proposal:

```python
prepared(cur,today,wa, *, subject=None,settings=None,mode='VALID',policy=True,
    policy_enabled=True,enabled=True,threshold='1',local_quiet=False,
    issue80=False,collect=True)
successor(cur,x,qty='3')
stage_existing(cur,today,wa,x, *, subject=None,collect=True)
original_unchanged(cur,x)
assert_detail(alert,x,reason=REVIEW_REASON,gross='186')
assert_notice_text(body,x,gross='186')
```

`settings=None` creates/configures an active owner before every source write
and capture. Supplied `settings={owner,user}` skips initial settings/key and
transport setup. Use it with `subject=<real Auth owner>`, `enabled=None`,
`collect=False` for a browser/HTTP fixture that must select/save WA settings
through the actual UI/Auth path. The fixture still saves the explicit rule
through the existing public facade and builds its condition set normally.
Transport then drives `wa.drain` after the user's settings save.

`prepared` returns `s,f,r,m,c,key,document,source_subject,boundary,ticks` plus
execution context and optional policy proof. `f` retains only the necessary
root/model/size/category/BOM/issue references. BOM `at` is ISO text, so the
proof can be JSON-round-tripped. `successor` does not commit or roll back and
therefore exposes the genuine BF writer locks to the caller's race.

The six Native cases prove gross186=93*2 ASSUMED with all coverage UNKNOWN;
missing versus explicitly empty BOM; stale successor186/fresh279 and complete
inactive/ambiguous source reviews; real current app-actor permissions; actual
receipt80/issue80 without invented installation; partialFG1 hold and FG93
resolution; current policy, local/WA quiet separation, replay and dedup.
Changed/unknown/policy-off notices stay OPEN and unattempted in the same
episode/outbox. Only genuine RESOLVED_NOW closes them. Later policy enabling
uses a fresh staged analysis; same-DONE rescan is not required.

The raw detail is exactly20 frozen keys. The Native source facts and public
recheck are read through the existing facades. The compact WA line has an
independent literal expected copy, including the20-character label prefix,
UNKNOWN external quantity and labelled BOM assumption. It never treats a
source-review notice as a threshold-met or purchase-quantity statement.

Validation performed here: Python AST syntax; actual imports against the
repository scripts with bytecode disabled; all facade names and six closure
IDs present; exact20 detail keys; the48+6 unique Native ID list. The first
import attempt from the scratch parent correctly failed because historical
modules require the repository working directory; repeating from the repo
root passed. No database, Native case, provider, HTTP or browser was run.

Administrative invalid-master and private-reader-fault subcases are labelled
inside the code and fully rolled back. They do not assert accepted BF-writer
creation of corrupt data. Provider responses written in the savepoint dedup
case are explicitly SYNTHETIC_PROVIDER_ANSWER; actual fake-provider receipt
belongs to the separate committed transport race.

Execution evidence records privileged fixture setup current/session identity
separately from the authenticated public RPC context. It records the actual
`postgres.rolsuper` flag. `postgres_definer_non_superuser` is false when that
role is SUPER; such a run cannot qualify the non-superuser postgres-definer
proof, even if the authenticated outer call is non-super. The genuine-stack
checkpoint must require that qualification true. This proposal never alters
roles or grants helper setup/writer privileges to make that proof pass.

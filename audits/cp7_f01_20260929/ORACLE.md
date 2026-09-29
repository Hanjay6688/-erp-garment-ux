# Independent family 1 oracle — P00/P01/P02, 29 September 2026

Frozen product: 735056db3b42cc7fc3999149b42e2cadac7b42b2.
Checkpoint: 88543e40320330e0cd95eae0bd54267f5f22d834 (documentation only).
This is an independent cross-check, not a claim of blind review: the checkpoint
and writer's stated scope/results have been read. Expected behavior below comes
from framework P00/P01/P02, E09/E14/E15/E20/E22/X09 and the preserved owner contract.
No product modifications; isolated disposable runtime only.

1. Receipt: preserve accepted CP6 product/package bytes and 48 source digests.
   Frozen checkpoint source/test/workflow hashes must bind the tested code.
2. One capture is internally coherent across source domains even under competing
   commits. After a blocking request wait, capture observes one coherent current
   source statement; never a mixture or data silently excluded by request-start
   time. No historical AS_KNOWN support is inferred.
3. Captured facts stay immutable. New writes/deletes/backdates/status/cost changes
   can mark the relevant authorized projection stale; they cannot rewrite its
   archived facts or silently present it as current.
4. Access is checked on capture, read, replay and after a request wait. Null,
   inactive, revoked, unmapped and unauthorized actors must receive no data.
   Another actor's run is not readable. A valid JWT alone is insufficient.
5. An operations capture must not collect or persist financial facts. Current
   financial denial hides values AND counts, hashes, stale signals and private
   references. Gaining finance access cannot manufacture missing cost facts from
   an older operations capture. OWNER retains authorized data.
6. Same actor/request/payload has one immutable effect. Same request with changed
   root rejects. Request/cursor/run/domain binding cannot be crossed, modified or
   truncated into a misleading complete page. Repeated pages are stable.
7. 0/1/100/101/500 source boundaries are complete within the declared domains;
   more than 500 is explicitly refused without a partial captured run. Missing,
   conflicting or malformed sources never become a known zero or COMPLETE.
8. UNKNOWN costs remain UNKNOWN, distinct from explicit zero/free. Exact physical
   root, size, source keys and decimal values survive transport unchanged.
9. Capture/read/stale checks cannot change operational rows, counters, stock,
   reservations or financial books. The dedicated compute principal cannot invoke
   mutators or write business tables even when the actor has broad privileges.
10. Private tables and internal helpers remain inaccessible through ordinary
    authenticated/anonymous REST. Public facade roles and current permissions,
    not service-role shortcuts, determine outcomes.
11. Cleanup, auth/schema restoration, package installation/backup-restore and
    original gates retain their actual outcomes. Fixture failure is INCOMPLETE,
    a disproved invariant is FAIL; neither is silently converted to PASS.

Scope: one physical root/exact size, CURRENT, bounded operational/cost domains.
No acceptance of WIP/forecast, shared capacity, report/apply/export/ACK, R10 UI,
arbitrary historical knowledge, all ERP domains or production operation. Existing
writer scenarios rerun by the auditor retain their provenance. New probes and
read-only log cross-checks are reported separately.

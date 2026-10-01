# Linked Native plan versus actual candidate

This implements the next P08 contract after the qualified22 Native draft bridge. Actual Native35 qualification is still pending. Full F04 material recipe/source feasibility and reviewed model integration remain open; no full-family, independent or production acceptance is claimed.

The public read `erp_cp7_read_plan_actual_v1(uuid)` takes only the actor's immutable saved draft ID. It compares the operator's immutable planned quantity with the one Native cutting group referenced by that draft's immutable intent. The original product physical root and exact size are mandatory. Other cutting groups, other PO quantities, commercial aliases and present warehouse FG stock cannot fill this plan's actual result.

The existing conserved Native WIP graph supplies every physical quantity. A saved estimate or unposted Native draft is NOT_STARTED with proven zero physical input, not production equal to the estimate. After real Native material POST, exact-size input must equal WIP + FG + BS + withheld + exited. The graph already conserves partial pickups, deliveries, receipts, QC, rework, failed laundry attempts, claims and dispositions. FG identity is proven from actual QC or the Native rework/disposition lot's product. A different physical root remains other-root FG; an unproven root keeps matched FG and remaining-to-plan UNKNOWN. Missing, deleted, future or incomplete Native sources stay UNKNOWN without a zero fallback. The pre-laundry group pool explicitly does not invent an exact sewing substage.

The one outer SQL statement binds capture time, Native header, raw physical facts, conserved graph and FG identity to one MVCC snapshot. No new stock, money, HPP or cost engine exists. Current four operational permissions, cutting view, own immutable Original and that Original's protected finance/preflight permissions are checked before and after capture. Stale Originals may be compared with current physical results; current loss of protected authority cannot be laundered through this operational projection. The private source helper belongs to the existing read-only capture role. The actor-facing read belongs to the existing plan writer; neither adds Native DML privileges or a new capture-to-mutator capability.

The UI loads only after an explicit comparison request. It retires quantities, comparison, current choices and parent FG/HPP during reads, source replacements, shared recovery/storage invalidation and current403. Own unsent notes remain. The client validates a closed receipt, exact actor/draft/run/intent/root/size bindings, known/unknown shape, the server's conservation and exact remaining receipt using integers. It cannot manufacture physical facts or new financial values. Production disposition is labelled separately from current warehouse availability and installed material proof.

| Fixed Native35 budget declared before execution | Count |
|---|---:|
| Existing draft bridge database cases |14|
| New linked-actual database cases |8|
| Actual two-connection races, existing5 + new2 |7|
| Real Auth/PostgREST, existing1 + new1 |2|
| Desktop/mobile, existing2 + new2 |4|
| Total |35|

New database cases cover saved/unposted zero, real two-piece cutting POST, one-piece pickup/sewing/laundry/receipt/QC, another root, lawful deletion, current/private authority, protected Original authority and explicit administrative future-source corruption. The two controlled gates instrument only the private CP7 capture reader and restore its exact definition. They prove a coherent pre-POST snapshot while a real Native POST commits, and refusal after cutting-view revocation during an observed public-read wait. No Native ERP writer or capture oracle is replaced. Both new browser journeys retain exact lost-apply UUID/remount recovery and then compare real cut2/WIP1/FG1 before current403 retires the view and preserves own notes.

Only master records and Native work drafts are seeded in the disposable fixture. Every material, pickup, sewing terminal, laundry, receipt and QC movement uses unchanged Native commands. The new two-piece PO is declared before Original capture, so it cannot reuse the predecessor's already completed hundred-piece work. The fixture's zero work rate is explicitly synthetic and never becomes an inferred factory tariff. Read-only checks compare the complete Native boundary, not only visible quantities. Local50 parser/DOM cases, TypeScript, build and security are stand-ins; the fixed35 runtime, installation, exact restoration, primary, backup, advisor, Auth cleanup and visual gates remain mandatory.

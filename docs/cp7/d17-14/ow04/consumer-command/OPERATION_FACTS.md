# Pending consumer facts and one-call posting scope

consumer/02_operation_facts.sql defines five private tables: the outer request,
its temporary context, immutable operation inputs, a one-call Native posting
scope and immutable actual completion. The installer does not load the file;
its explicit complete-composition barrier remains. No public command, native
admission, money use, deferred closure or feature completion is implemented.

The request identity covers action, canonical payload and document versions.
Only request/context tables belong to the existing private outer writer role.
Financial operation/completion tables stay postgres-owned, RLS-denied and append
only, including TRUNCATE. Source/target roots and current leaves are distinct
from immutable event target IDs. Cash/AR accounts are actual snapshots; no new
default account or expiry policy is defined. Signed UNDO requires an original
event reference. Amount is an unbounded cent domain, so subcents cannot round
into an accepted value. Economic date follows explicit physical WIB date;
book date cannot precede it. These structural checks do not prove source truth.

Seventeen local PGlite schema/constraint controls use minimal FK stub tables and
explicit dummy provenance. They check private RLS/ACL/ownership, exact monetary
shape, required target/cash pairing, date consistency, liability collision,
operation immutability including TRUNCATE CASCADE and duplicate actor/request
identity. They are NOT Native business documents or a source-authority proof.

Before load, implement current permissions after every wait, full source graph
and HPP locks before period, exact Native callbacks, actual source-dependent
negative amount/kind/dimension/timing validation, all dated family targets,
materialization dispatch, completed UUID replay and context-free deferred
closure with every temporary scope cleared. A valid table row alone authorizes
nothing. No unconditional-success validator or closure placeholder is supplied.

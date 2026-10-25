# Separate private stock reference v2 preparation

This is not installed or runtime qualified. Existing v1 source and all v1
archives remain unchanged. A v2 hash is intentionally different and may never
be compared to a v1 hash or substituted under the v1 contract.

The generator derives the exact existing 15-field projection, root guards,
UUID row order, both visibility clocks and private owner/ACL from a pinned v1
helper. Each normalized record retains its field OID, signed length, NULL
marker and bytes. UUID, timestamp and int64 use built-in PG17 types; the four
textual fields are explicitly converted to UTF8 bytea before record_send, so
client_encoding and private enum OIDs cannot affect the bytes. The outer
framing includes the version, encoding and complete layout hash.

Only PG17 with UTF8 server encoding and the exact built-in type identifiers
is admitted. Controlled PGlite18 measurements are separate experimental
evidence; this helper must refuse that server. No compatibility or latency
qualification for Native PG17 follows from that experiment.

Before any caller integration, qualify a closed isolated Native suite: exact22
catalog/inverse/ACL, independently decoded Native fields and NULL/wide int64/
UTF8/microsecond/infinity controls, all15 field mutations, both clocks and late
visibility, bad scope/duplicate/null roots and sorted UUIDs, synthetic1200x3
full-volume old/new/ new/old timings under unchanged8s. Preserve all successful
and failed observations. No fastest-run selection, changed policy, fake model
winner, official finance or factory-SLA credit. Existing v1 must remain exact.

The bounded source, work fingerprint, request/replay and unit consumers still
require an explicitly versioned adapter before this reference can be used.
Deterministic compilation may only be deferred from a complete frozen SQL
summary and captured non-stock facts into existing job outputs; jobs.reference
stays immutable. Never re-read live stock by clock alone in a later unit.

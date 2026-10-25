# Frozen analysis source v2 — private preparation

This separate namespace captures the complete existing non-stock source, the
qualified PG17 binary full-stock reference, and the complete SQL stock summary
in one STABLE source call. It seals them with the exact query, capture instant,
producer identity and an explicit version 2 capsule hash. Raw Native INCOMPLETE
stays INCOMPLETE; input coverage stays PENDING until preparation succeeds.

The pure `prepare` helper verifies the entire capsule and calls the unchanged
current `cp7_history_bounded.compile` with those frozen arguments. It has no
table read, current-clock read, or source recapture. Its existing kernel,
availability, quantity, model and analog logic remains unchanged. Admission is
derived from that actual compiler, including all non-stock overflow, duplicate
root, ambiguous commercial identity and original sale-journal guards.

The work fingerprint has an explicit version 2 domain. It binds the same Native
work source, full-stock rows and producer; the capture clock and selected query
stay outside work-calendar identity. Old version 1 functions and archives are
untouched. The full capture clock and query are bound in the capsule itself.

The package has eleven private functions, one schema, no table or public RPC,
and no existing-function replacement. Nothing installs it by default or calls
it from the ERP request/unit routes. Integration needs its own explicit
versioned adapter, immutable-reference/cache lifecycle and runtime qualification.
Local binding controls do not qualify Native capture, access races, factory
performance, finance/HPP, after-use restore, or production.

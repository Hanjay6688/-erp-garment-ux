# Version-bound evaluation selection

Two private functions, no public method/table/replacement/default installation.
`latest` selects the newest actor-owned evaluation per physical target across
the immutable global-v2 and scoped-v3 tables. It never searches backwards for a
winner. Exact timestamp ties prefer v3, then descending UUID within the runtime.
The version and exact reader method are part of the reference identity.

`current` checks current access, rejects a cutoff superseded by a newer run,
delegates to the selected runtime's existing immutable reader, binds the reply,
then rechecks access, selection and the WIB date. It performs no forecast math,
history recapture or business write. The original assessment/current guard remain
separate. Each consumer must still bind its own captured physical inputs and
history query and use the existing shared target projection kernel.

The next target adapter must carry the versioned reference through source hashes,
baseline/reorder/staged provenance and cache revalidation. Never reinterpret an
old v1 target-source row as this reference, or look up a UUID without its runtime.
This component alone does not integrate the target caller or qualify Native,
Auth, concurrency, after-use restore, model accuracy or production use.

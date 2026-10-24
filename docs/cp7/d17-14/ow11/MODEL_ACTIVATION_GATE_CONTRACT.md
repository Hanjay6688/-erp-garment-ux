# Model activation admission prototype

Two private functions and one private schema, zero public functions/tables/old
replacements. No connection, default installation, registry insertion, policy
creation or forecast caller. This is not full OW11a or a factory policy.

The existing Native registry is a technical proposal; its timestamp and default
promotion numbers are not owner approval. An eventual owner configuration must
record minimum training days, maximum horizon, explicitly permitted methods, all
five existing promotion settings and a reason. Empty allowed methods permits no
challenger. No values are filled in as a factory default. The policy identity,
revision and actual recorded clock must be embedded in its prospective registry.
Acceptance after registration cannot make old validation prospective.

The gate binds current physical target/size, Native source and engine hashes,
knowledge cutoff, exact tested horizon and forecast start on the current WIB
business date. A vector computed for yesterday is not moved to today. The existing
Native build/evaluation is recomputed from its immutable input before admission;
changed selection, metrics, forecasts or holdout flags fail. Native evidence uses
actual historical capture clocks and keeps censored/unknown periods unknown.

Only a challenger selected by complete paired chronological validation, explicitly
allowed by the policy, with sufficient current training and a complete separate
holdout can be ELIGIBLE. Holdout scores are not used to select or retune the model.
Missing/suspended policy, old source, late registration, short history, ineligible
current training, wrong horizon/origin or baseline ties require the existing
baseline with a reason. The forecast vector is retained; it is never reduced to
a single mean that loses its day positions. All output still says applied=false.

Local actual SQL: 13 cases PASS, including expected NAIVE forecast100 for each of
seven days and paired MAE4 on explicitly synthetic increasing data; forged results,
prospective policy identities, one-microsecond timing, current-only knowledge,
censored periods, tie, horizon/origin, bounds and method refusals. The first local
bootstrap duplicate-schema failure is preserved. SQL/PLpgSQL parse/clash PASS.
This establishes neither Native captures nor real owner policy, Auth/catalog22,
business accuracy, active model use, full A chain or independent acceptance.

Next implementation must add immutable owner policy/CAS/UUID/current access and
a prospective registry adapter; no backdated capture/registry rows. Consumers must
respect manual/own/analog priority and consume dated horizon sums through the one
target kernel with one buffer and one supply allocation. Legacy results and exact
request-method identities remain immutable. Admission must be cached with its
immutable proof identity so the model is not recomputed per target row or UI read.

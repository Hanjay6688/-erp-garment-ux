# Immutable scoped model evaluation

Four private functions, two authenticated public facades and one private RLS
immutable table retain evaluations from the scoped single-product history.
The v3 request namespace, table and history foreign key are separate from v1
and v2. Existing models, default installation and target callers stay unchanged.

The existing policy binder, model assessment and dated admission guard remain
authoritative. Actual history capture times remain knowledge times. A later
policy cannot approve an older capture; UNKNOWN observations never become zero.
No new policy values, forecast method or activation threshold is supplied.

Before extending the engine identity, the wrapper verifies the exact scoped
input digest. The retained assessment is returned unchanged. A separate current
guard rechecks source, policy, model engine, current day and actor access. New
capture holds the global envelope then actor/method/request lock; checks access
after each wait; requires exact payload on replay; and verifies current inputs
after the final insert. A refusal rolls back the entire model insertion.

Local8PASS uses actual scoped history/model SQL with controlled ERP/Auth
primitives. First failure (1PASS/7FAIL) exposed SQL operator precedence in a
JSON guard comparison; parentheses fix the product expression. A subsequent
7PASS/1FAIL matched the wrong immutable-error name; the test now requires the
existing CP7_RUN_IMMUTABLE contract. Both first logs are retained outside git.
Local evidence is not actual Native/Auth/concurrency or installer qualification.

The separate Native6 declaration covers exact22 composed installation/inverse,
actual capture/replay/immutable rows, prospective policy, actual SALE and current
access, synthetic2000/202000 scale under unchanged8s, and final-insert fault plus
engine change. The installer declares the four parent foreign-key triggers,
uses RESTRICT/savepoint atomic inverse and refuses removal after retained use.
After-use backup restore, Auth/concurrency, public client and model-target
consumption remain open. Full OW11 and production acceptance remain false.

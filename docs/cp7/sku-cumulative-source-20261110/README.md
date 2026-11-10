# SKU Native25 — cumulative Mandor source preparation

This checkpoint restores the exact closed SKU preparation tree `ebefa23ce99443f74b32e52e8fabebbc23f32d4d` from commit `1b9d6d18ce206b2a117e0010409540e695ae1c95`, then applies the opt-in cumulative source intake repair. The four recovered commits are `57e2e69feded98fbe89c17a203d4b9258002a108`, `ef43dedff4148be052c4ed30e923e6742e5c3aaf`, `0e7693f9cdbbb4e5a7f7ec79b354894a6d37f233`, and `1b9d6d18ce206b2a117e0010409540e695ae1c95`. Original bundle identities remain in intake V105.

## What is implemented

`cumulative_parent.py` validates the exact original review and derives a source-stage Root for 15 retained backend cases plus the two successful paired browser cases. `source_intake.py --cumulative` selects the cumulative contract in the private retained money bridge; money-case, graph, and network/database checks remain enforced. The original admission module and legacy single-run path remain unchanged.

The original backend run `42660429648` remains failed. Browser run `42752853455` and its original archive verification run `42770344036` are separately identified. This is cumulative evidence, never a fabricated successful single run. The included Root has `runtime_admission=false`, `production_go=false`, and `independent_acceptance=false`. It must not be used to launch a qualification.

## Verification

From the repository root:

```sh
python -B docs/cp7/sku-cumulative-source-20261110/verify_patch.py . docs/cp7/sku-cumulative-source-20261110/MANDOR17_PARENT_ROOT_ACTUAL_INTAKE.json
(cd scripts/current-sku-automatic-composite-preparation && python -B -m unittest test_source_intake test_qualification.OwningNative25.test_closed_and_every_partial_entry_refuses_before_any_receipt_read test_qualification.OwningNative25.test_money_binding_closed_gate_never_inspects_receipts_or_loads_retained_modules test_qualification.OwningNative25.test_private_function_code_and_original_admission_are_unchanged)
```

The source patch passed seven existing tests and twelve tamper controls using the actual original money intake. The archived intake adapter change is retained in `SKU_CUMULATIVE_ADOPTER.patch`, applied relative to intake V105.

## Remaining work before qualification

The complete physical source observer must adopt the exact 33-path Mandor backend delta in `BACKEND_SOURCE_DELTA.json`. Its previous six-path/single-run fence is not equivalent to the latest backend and paired browser candidate. Runtime cumulative provenance, complete no-network/no-database source observation, and applicable independent acceptance remain open. No SKU workflow is installed by this checkpoint; no SKU or Global qualification is claimed. Formal CP7 remains 5/16.

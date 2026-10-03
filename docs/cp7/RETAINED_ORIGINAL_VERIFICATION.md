# Qualified retained-Original verification

scripts/cp7_verify_retained_originals.py is a read-only checker invoked by the exact artifact projection workflow before upload. It accesses no database, calls no ERP operation, writes no proof, and gives zero new Native/product execution credit.

It verifies the actual retained envelope/gzip/root/archive-member hashes; source/run/tree/bundle pins; all cases against planned identities, observed counts and budgets; complete package/restoration/primary/backup/advisor/Auth cleanup gates; browser console; and the explicit zero-credit diagnostic/projection classification. JSON duplicate members are refused. A manifest supplies an external exact source/archive/budget pin where passed. Internal consistency alone is not independent proof of business reality or auditor acceptance.

The checker requires PASS; it does not relabel an INCOMPLETE Original. Historical failed artifacts remain retained by the unchanged projection/retention path and are not passed to the qualified-only validator.

The projection workflow calls:

```bash
python scripts/cp7_verify_retained_originals_test.py
python scripts/cp7_verify_retained_originals.py cp7-proof/native152 --manifest docs/cp7/native152_artifact_projection.json --projection-head "$GITHUB_SHA"
python scripts/cp7_verify_retained_originals.py cp7-proof/native284-qualified-current --manifest docs/cp7/native284_latest_qualified_artifact_projection.json --projection-head "$GITHUB_SHA"
```

All12 local synthetic corruption/refusal controls pass. They check gzip/root corruption, wrong external source, false backup gate, Auth leak, missing/renamed actual case, undeclared extra group, failed Original, diagnostic product credit, missing pinned projection and a positive read-only result. These controls are tooling tests, not Native/business cases.

Current actual retained Native57/40/69, diagnostic2 and F05 Native152/284 receipts also pass the checker locally.152 and284 have exact manifests/source/archive pins; diagnostic2 explicitly keeps zero product credit. Shell Originals are checked separately against actual CI logs/browser JSON/private-kernel report/CodeQL SARIF, not treated as a business runtime receipt.

Native/report SQL, app, every case budget/full54 request and frozen CP5/CP6 remain unchanged. Workflow permissions remain contents/actions read. Fresh same-source verifier CI is required after publication; local validation is not that CI result, full P18/P19, independent P20 or installed P21.

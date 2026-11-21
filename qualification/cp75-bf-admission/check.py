"""Exercise admission and both provider paths on disposable, pinned source checkouts."""
from contextlib import contextmanager
from pathlib import Path
import json
import os

import calendar_probe
import global_preseal
import reviewed_ordinary as licensed
from global_owning import owning


@contextmanager
def changed(path):
    original = path.read_bytes()
    try:
        path.write_bytes(original + b"\n")
        yield
    finally:
        path.write_bytes(original)


def refusal(label, call, path, expected):
    with changed(path):
        try:
            call()
        except (ValueError, RuntimeError) as exc:
            if str(exc) != expected:
                raise
            return dict(control=label, refusal=str(exc))
    raise AssertionError(f"{label} unexpectedly passed")


def main():
    work = Path(os.environ["GITHUB_WORKSPACE"])
    temp = Path(os.environ["RUNNER_TEMP"])
    result = temp / "admission-results"
    result.mkdir(exist_ok=True)
    release, sku, candidate = work / "provider", work / "sku", work / "candidate"
    inputs = release / "qualification"
    global_preseal.materialize(sku, candidate, inputs / "global-preseal/global-combined.patch.gz")
    owning.git(candidate, "sparse-checkout", "add", "docs/cp7/d17-14/ow04/consumer-command",
               "docs/evidence", "supabase/migrations", "supabase/tests")
    parent = (release / licensed.ROOT_PATH).read_bytes()
    profile = (release / licensed.PROFILE_PATH).read_bytes()
    catalogue = (temp / "sku-catalogue.json").read_bytes()
    day = calendar_probe.confirmed_factory_day(
        temp / "cp75-original-observations", "44912039412", "7f0baf7a3fcfe82f5ec48500ae45bdd8a3b41c8b")

    def admit():
        return licensed.admit(candidate, sku, parent, profile)

    manifest = admit()
    owning.source_files(candidate)
    historical = "qualification/global_owning/SOURCE.json"
    assert len(manifest["immutable_runner_inputs"]) == 47
    assert manifest["immutable_runner_inputs"][historical]["sha256"] == "46631f8119bc4537a08fb2806f315027568b12348aa561f26f1f437bed229505"
    assert day.isoformat() == "2026-11-20"
    def restored():
        return owning.prepared_provider(candidate, parent, catalogue, restored_source_day=day)

    fresh_provider, fresh_proof = owning.prepared_provider(candidate, parent, catalogue)
    restored_provider, restored_proof = restored()
    assert fresh_proof == restored_proof and restored_proof["root"] == licensed.ROOT_PIN
    assert fresh_provider._automatic_parent_catalogue.__module__ == "realtime_comparator"
    assert restored_provider._automatic_parent_catalogue.__module__ == "cp75_original_bf_realtime"
    controls = [
        refusal("historical source manifest changed", admit, release / historical,
                "GLOBAL_ORDINARY_REVIEW_INPUT_PIN_CHANGED:" + historical),
        refusal("reviewed profile changed", admit, release / licensed.PROFILE_PATH,
                "GLOBAL_ORDINARY_REVIEW_INPUT_PIN_CHANGED:" + licensed.PROFILE_PATH),
        refusal("restored comparator changed", restored, inputs / "cp75_bf_realtime.py",
                "GLOBAL_PRESEAL_SOURCE_DIGEST_CHANGED:cp75_bf_realtime.py"),
        refusal("partition checker changed", restored, inputs / "daily_partitions.py",
                "GLOBAL_PRESEAL_SOURCE_DIGEST_CHANGED:daily_partitions.py"),
    ]
    assert admit() == manifest
    report = dict(immutable_inputs=47, relations=manifest["relations"]["count"],
                  original_bf_sql_run=44912039412, recovered_source_day=day.isoformat(),
                  combined_tree=owning.COMBINED, fresh_provider=fresh_provider._automatic_parent_catalogue.__module__,
                  restored_provider=restored_provider._automatic_parent_catalogue.__module__,
                  negative_controls=controls, production_go=False)
    (result / "admission.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()

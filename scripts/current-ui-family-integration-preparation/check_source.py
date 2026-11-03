"""Admit the exact presentation derivation, never a financial runtime receipt."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "docs/cp7/d17-14/ui-a-integration-20261103/SOURCE.json"
CHECK = "scripts/current-ui-family-integration-preparation/check_source.py"
ENV = dict(os.environ, GIT_NO_LAZY_FETCH="1")


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], env=ENV)


def pin(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    m = json.loads((ROOT / MANIFEST).read_text())
    assert m["contract"] == "cp7.A.presentation-integration-source.v1"
    assert m["unified_runtime_admission"] is False and m["production_go"] is False
    base, original, donor = m["A_base_local_commit"], m["original_theme_base"], m["B_candidate"]
    assert git("rev-parse", base + "^{tree}").decode().strip() == m["A_base_tree"]
    assert not git("diff", "--name-only", original, base, "--", "src").strip()
    expected = set(m["presentation_derivations"])
    assert set(git("diff", "--name-only", original, donor, "--", "src").decode().splitlines()) == expected
    changed = set(git("diff", "--name-only", base).decode().splitlines())
    changed.update(git("ls-files", "--others", "--exclude-standard").decode().splitlines())
    assert changed == expected | {MANIFEST, CHECK}, sorted(changed ^ (expected | {MANIFEST, CHECK}))
    for name, pins in m["presentation_derivations"].items():
        assert name.endswith(".css") or name in {
            "src/App.tsx", "src/main.tsx", "src/OperationsAdminPages.tsx",
            "src/MobilePrimaryNavigation.tsx", "src/MobilePrimaryNavigation.dom.test.tsx",
        }, name
        raw = (ROOT / name).read_bytes()
        assert pin(raw) == pins["after"], name
        assert raw == git("show", donor + ":" + name), name
        if pins["before"] is not None:
            assert pin(git("show", base + ":" + name)) == pins["before"], name
    # Compare every src file, including runtime consumers outside the style delta.
    donor_sources = git("ls-tree", "-r", donor, "--", "src").decode().splitlines()
    for entry in donor_sources:
        metadata, name = entry.split("\t", 1)
        expected_blob = metadata.split()[2]
        actual_blob = git("hash-object", str(ROOT / name)).decode().strip()
        assert actual_blob == expected_blob, name
    for name, blob in m["identical_build_inputs"].items():
        assert git("rev-parse", base + ":" + name).decode().strip() == blob
        assert git("rev-parse", donor + ":" + name).decode().strip() == blob
        assert git("hash-object", str(ROOT / name)).decode().strip() == blob
    for name, blob in m["retained_original_UI_receipts"].items():
        assert git("hash-object", str(ROOT / name)).decode().strip() == blob, name
    settings = (ROOT / "src/OperationsAdminPages.tsx").read_text()
    assert settings.replace('title="Pengaturan ERP"', 'title="Pengaturan ERP yang bisa dipertanggungjawabkan"') == git("show", base + ":src/OperationsAdminPages.tsx").decode()
    main_source = (ROOT / "src/main.tsx").read_text()
    assert main_source.replace("import './theme.css'\n", "", 1) == git("show", base + ":src/main.tsx").decode()
    print(json.dumps({
        "status": "EXACT_B_PRESENTATION_ON_A_PREPARED_BASE",
        "presentation_paths": len(expected), "entire_src_files_equal_B": len(donor_sources),
        "A_financial_or_workflow_changes": 0,
        "retained_original_UI_receipts": len(m["retained_original_UI_receipts"]),
        "unified_runtime_admission": False, "actual_financial_cases": 0, "production_go": False,
    }))


if __name__ == "__main__":
    main()

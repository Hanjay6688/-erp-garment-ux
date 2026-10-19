"""Forward the unchanged K4 fixture payload and save its read-only wait observation."""
import hashlib
import io
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parent
PRODUCT = ROOT.parents[2] / "auditor"
sys.path.insert(0, str(PRODUCT / "scripts"))
import cp7_schedule as schedule
from q1_state_observer import observe


def main():
    fixture = PRODUCT / "scripts/cp7_k4_runner_browser_fixture.py"
    declaration = json.loads((ROOT / "Q1_STATE_PREEXECUTION_MANIFEST.json").read_text())
    assert hashlib.sha256(fixture.read_bytes()).hexdigest() == declaration["frozen_product_sources"]["scripts/cp7_k4_runner_browser_fixture.py"]
    operation, payload = sys.argv[1], json.load(sys.stdin)
    label = payload.pop("_sol_metadata_case_id", None)
    allowed = {row["id"] for row in declaration["cases"] if row["mode"].startswith("BROWSER")}
    assert label is None or label in allowed, "SOL_Q1_UNKNOWN_METADATA_LABEL"
    assert label is None or operation == "runner_off", "SOL_Q1_LABEL_ON_NON_OBSERVATION"
    sys.argv = [str(fixture), operation]
    sys.stdin = io.StringIO(json.dumps(payload))
    if operation == "runner_off":
        label = label or "SOL_R4_Q1_UNLABELLED_FINALLY"
        output = PRODUCT / "cp6-proof/t3" / (label + ".jsonl")
        with observe(schedule, label, output, "cp6_auditor_browser"):
            runpy.run_path(str(fixture), run_name="__main__")
    else:
        runpy.run_path(str(fixture), run_name="__main__")


if __name__ == "__main__":
    main()

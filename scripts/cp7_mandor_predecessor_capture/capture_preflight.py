#!/usr/bin/env python3
"""Source-only admission for the capture-only disposable workflow."""
from __future__ import annotations

import json
import sys

from capture_identity import admit


def main() -> int:
    sys.path.insert(0, str(admit()))
    import qualification
    fence = qualification.load(
        "cp7_capture_exact_source_network_db_fence",
        qualification.FROZEN / "scripts/current-sku-managed-recovery-native27-qualification/source_context.py",
    )
    with fence.fenced_source_read() as guard:
        engine = qualification.runtime()
        with engine.inherited_admission.parent_scope():
            proof = engine.admitted()
    print(json.dumps({"status": "CAPTURE_SOURCE_ADMITTED", "source": proof, "source_DB_guard": guard, "actual_SQL_executed": 0, "production_go": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

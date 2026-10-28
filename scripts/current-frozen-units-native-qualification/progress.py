"""Bounded phase diagnostics; never an Original or a qualification result."""
from datetime import datetime, timezone
import json
from pathlib import Path
from time import monotonic

PHASES = frozenset((
    'PACKAGE_START', 'PACKAGE_RETURNED', 'WRITER_RUNTIME_START', 'SOURCE_ADMITTED',
    'BASELINE_CAPTURED', 'PREINSTALL_DUMP_READY', 'INSTALL_1_RETURNED',
    'PREUSE_INVERSE_RETURNED', 'INSTALL_2_RETURNED', 'INSTALL_COMMITTED',
    'NATIVE_GROUP_STARTED', 'NATIVE_GROUP_RETURNED', 'USED_GUARD_CHECK_RETURNED',
    'WRITER_ERROR', 'RESTORE_STARTED', 'BASELINE_RESTORATION_CHECKED',
    'RESTORE_ERROR', 'ORIGINAL_WRITTEN',
))


class Progress:
    def __init__(self, path):
        self.path = Path(path)
        self.started = monotonic()
        self.sequence = 0

    def mark(self, phase):
        if phase not in PHASES:
            raise ValueError('UNDECLARED_QUALIFICATION_PHASE')
        self.sequence += 1
        event = dict(diagnostic_only=True, phase=phase, sequence=self.sequence,
                     elapsed_seconds=round(monotonic() - self.started, 3),
                     recorded_at_utc=datetime.now(timezone.utc).isoformat())
        line = json.dumps(event, sort_keys=True)
        # Diagnostics must not suppress a business exception or prevent restore.
        try:
            print('CP7_QUALIFICATION_PHASE ' + line, flush=True)
        except OSError:
            pass
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open('a', encoding='utf-8') as f:
                f.write(line + '\n')
        except OSError:
            pass

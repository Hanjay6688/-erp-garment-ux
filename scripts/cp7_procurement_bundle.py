"""Explicit P09 development bundle; accepted CP6 posting functions stay authoritative."""
from pathlib import Path
import cp7_wip_bundle
ROOT=Path(__file__).resolve().parents[1]
FILES=('bootstrap.sql','accepted-deltas.sql','read.sql','command.sql','ownership.sql')
REPLACED=('erp.require_internal()','erp.bc_guard_zone_location_v1()')
def extension():
    procure=ROOT/'scripts/cp7-src/procurement';material=ROOT/'scripts/cp7-src/materials'
    return '\n'.join(p.read_text() for p in [procure/'bootstrap.sql',material/'bootstrap.sql',
      *[procure/f for f in FILES[1:]],*[material/f for f in ('read.sql','transfers.sql','command.sql','ownership.sql')]])
def bundle():
    return cp7_wip_bundle.bundle()+'\n'+extension()

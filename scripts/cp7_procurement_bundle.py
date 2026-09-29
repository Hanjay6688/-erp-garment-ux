"""Explicit P09 development bundle; accepted CP6 posting functions stay authoritative."""
from pathlib import Path
import cp7_wip_bundle
ROOT=Path(__file__).resolve().parents[1]
FILES=('bootstrap.sql','read.sql','command.sql','ownership.sql')
def bundle():
    return cp7_wip_bundle.bundle()+'\n'+'\n'.join((ROOT/'scripts/cp7-src/procurement'/f).read_text() for f in FILES)

"""P10 read-only FG extension after the current explicit CP7 development bundle."""
from pathlib import Path
import cp7_procurement_bundle
ROOT=Path(__file__).resolve().parents[1]
FILES=('bootstrap.sql','read.sql','ledger.sql','ownership.sql')
def extension():
    return '\n'.join((ROOT/'scripts/cp7-src/fg'/f).read_text() for f in FILES)
def bundle():
    return cp7_procurement_bundle.bundle()+'\n'+extension()

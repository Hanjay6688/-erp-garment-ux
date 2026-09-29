"""Explicit P03 development bundle on the verified P02 foundation."""
from pathlib import Path
import cp7_snapshot_bundle
ROOT=Path(__file__).resolve().parents[1]
FILES=('bootstrap.sql','workspace.sql','history.sql','command.sql')
def bundle():
    return cp7_snapshot_bundle.bundle()+'\n'+'\n'.join((ROOT/'scripts/cp7-src/identity'/f).read_text() for f in FILES)

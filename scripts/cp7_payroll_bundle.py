"""Candidate P10 Nota / P12 native source increment; not a payroll release."""
from pathlib import Path
import cp7_fg_bundle
ROOT=Path(__file__).resolve().parents[1]
FILES=('source.sql','ownership.sql')
def extension():
    return '\n'.join((ROOT/'scripts/cp7-src/payroll'/f).read_text() for f in FILES)
def bundle():
    return cp7_fg_bundle.bundle()+'\n'+extension()

"""Nota composer extension over the source-qualified P12 stack; candidate only."""
import cp7_payroll_bundle
ROOT=cp7_payroll_bundle.ROOT
FILES=('notes.sql','note-read.sql','note-ownership.sql')
def extension():
    return '\n'.join((ROOT/'scripts/cp7-src/payroll'/f).read_text() for f in FILES)
def bundle():
    return cp7_payroll_bundle.bundle()+'\n'+extension()

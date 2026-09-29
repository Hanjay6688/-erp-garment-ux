"""P04 explicit development bundle; the authoritative kernels run in Postgres."""
from pathlib import Path
import cp7_identity_bundle
ROOT=Path(__file__).resolve().parents[1]
FILES=('bootstrap.sql','graph.sql','matching.sql','yield.sql','timing.sql','source.sql','rewash.sql','normalize.sql','bs.sql','facade.sql','other-source.sql','other-normalize.sql','production.sql','ownership.sql')
def bundle():
    return cp7_identity_bundle.bundle()+'\n'+'\n'.join((ROOT/'scripts/cp7-src/wip'/f).read_text() for f in FILES)

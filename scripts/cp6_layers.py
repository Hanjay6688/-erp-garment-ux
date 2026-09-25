"""Layer registry of the T1 families on the disposable chain: which later family replaces a function an earlier family
installed.

An earlier family verifies the exact text of the functions it installed only while no later family that replaces them is
installed; the later family then verifies its own text of those functions. The registry is keyed by the later family's
marker in erp.schema_migrations and read from its builder, never inferred from the catalog.
"""
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent))
import cp6_ba_build as ba
import cp6_bb_build as bb
import cp6_bc_build as bc

LATER={ba.VERSION:tuple(ba.REPLACED),bb.VERSION:tuple(bb.REPLACED),bc.VERSION:tuple(bc.REPLACED)}


def superseded(cur,after=None):
    """Signatures (regprocedure text) replaced by a later family installed on this database. `after`: only the families
    registered after that marker (a registered family verifying its own text must not skip what it replaced itself)."""
    order=list(LATER)
    scope=order if after is None else order[order.index(after)+1:]
    marks=[r[0] for r in cur.execute('select version from erp.schema_migrations where version=any(%s)',(scope,)).fetchall()]
    return {s for m in marks for s in LATER[m]}

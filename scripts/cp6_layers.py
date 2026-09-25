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

LATER={ba.VERSION:tuple(ba.REPLACED)}


def superseded(cur):
    """Signatures (regprocedure text) replaced by a later family installed on this database."""
    marks=[r[0] for r in cur.execute('select version from erp.schema_migrations where version=any(%s)',(list(LATER),)).fetchall()]
    return {s for m in marks for s in LATER[m]}

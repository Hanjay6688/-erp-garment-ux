"""Materialize the released products that compose the installed Global baseline."""
import os
import subprocess
from pathlib import Path

import global_preseal
from close11.source import materialize as materialize_global
from global_owning import owning
from p21 import g04_source, s06_source

WORK = Path(os.environ["GITHUB_WORKSPACE"])
ROOT = WORK / "sku-build"
RELEASE = WORK / "global-release"


def main():
    candidate = ROOT / "global-candidate"
    global_preseal.materialize(ROOT / "auditor", candidate, RELEASE / "qualification/global-preseal/global-combined.patch.gz")
    owning.git(candidate, "sparse-checkout", "add", "docs/cp7/d17-14/ow04/consumer-command", "docs/evidence", "supabase/migrations", "supabase/tests")
    patch = (RELEASE / g04_source.BUNDLE).read_bytes()
    g04_source.prepare(ROOT / "g04-product", patch)
    s06 = ROOT / "s06-product"
    subprocess.run(["git", "clone", "--quiet", "--shared", "--no-checkout", str(ROOT/"g04-product"), str(s06)], check=True)
    owning.git(s06, "sparse-checkout", "set", "src", "scripts", "tests", "contracts", "public", "supabase")
    owning.git(s06, "checkout", "--quiet", "--detach", g04_source.PRODUCT)
    s06_source.prepare(s06, (RELEASE / s06_source.BUNDLE).read_bytes())
    materialize_global(ROOT)
    print("CP75_GLOBAL verified accepted source products", flush=True)


if __name__ == "__main__":
    main()

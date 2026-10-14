"""Run exactly two newly declared claim date cases on the pinned FULL product."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.argv=[sys.argv[0],'integration']
import own_contracts as runner
runner.SUITES['integration']=['cases_claim_date']
runner.full_stack.package._writer_runtime=lambda browser_mode=False:runner.run()
runner.full_stack.package.run('install')

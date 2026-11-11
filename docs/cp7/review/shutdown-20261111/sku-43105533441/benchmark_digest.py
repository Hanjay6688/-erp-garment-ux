"""Compare old and new v1 digests against a retained SKU report."""
from hashlib import sha256
from pathlib import Path
from types import ModuleType
import json
import resource
import subprocess
import sys
from time import perf_counter, process_time

repo = Path(sys.argv[1]).resolve()
variant = sys.argv[2]
original = Path(sys.argv[3])
layers = int(sys.argv[4])
path = 'scripts/current-sku-automatic-composite-preparation/package.py'
base = 'd08032a28b9f00d0ee70a6f98c6b7d0f5b770c4a'
raw_source = (subprocess.check_output(['git', '-C', str(repo), 'show', base + ':' + path])
              if variant == 'd080' else (repo / path).read_bytes())
module = ModuleType('benchmark_' + variant)
module.__file__ = str(repo / path)
exec(compile(raw_source, module.__file__, 'exec', dont_inherit=True), module.__dict__)
raw = original.read_bytes()
assert sha256(raw).hexdigest() == '5e22077e71e34add6fd0627c89e9d21a2235f463818e45b233c7619bcfb0d48f'
actual = json.loads(raw)
state = {}
for index in range(layers):
    state = dict(predecessor=state, before=actual, after=actual, index=index)
started, cpu_started = perf_counter(), process_time()
digest = module.state_digest(state)
print(json.dumps(dict(variant=variant, package_sha256=sha256(raw_source).hexdigest(), layers=layers,
                      report_sha256=sha256(raw).hexdigest(), report_bytes=len(raw), digest=digest,
                      seconds=round(perf_counter()-started, 3), cpu_seconds=round(process_time()-cpu_started, 3),
                      peak_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss), sort_keys=True))

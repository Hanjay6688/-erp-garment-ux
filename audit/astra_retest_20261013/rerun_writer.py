"""Execute pinned writer cases unchanged, with read-only supplier boundary telemetry."""
from pathlib import Path
import sys, runpy, json, hashlib, traceback, copy
PRODUCT = Path.cwd().parent / 'auditor'
sys.path.insert(0, str(PRODUCT / 'scripts'))
probe = sys.argv[1]
sys.argv = [str(PRODUCT / 'scripts' / probe), *sys.argv[2:]]
if probe == 'cp7_supplier_payment_create_probe.py':
    import cp6_auditor_runner as native
    out = PRODUCT / 'cp6-proof/t3/ASTRA_SUPPLIER_BOUNDARY_OBSERVATIONS.json'
    observations = []
    def observe(original, kind):
        def read(cur):
            result = original(cur)
            safe = copy.deepcopy(result)
            if isinstance(safe, dict) and 'auth' in safe:
                raw = json.dumps(safe['auth'], sort_keys=True, default=str)
                safe['auth'] = {'count':len(safe['auth']), 'sha256':hashlib.sha256(raw.encode()).hexdigest()}
            observations.append(dict(kind=kind, caller=[dict(file=Path(f.filename).name, line=f.lineno, function=f.name) for f in traceback.extract_stack(limit=5)[:-1]], snapshot=safe))
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(dict(instrumentation='Read-only copies; original return object and equality unchanged', observations=observations), indent=2, default=str)+'\n')
            return result
        return read
    native.boundary.snapshot = observe(native.boundary.snapshot, 'boundary')
    native.public_state = observe(native.public_state, 'public_state')
runpy.run_path(sys.argv[0], run_name='__main__')

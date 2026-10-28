from pathlib import Path
import importlib.util,json
p=Path(__file__).resolve().parent/'probe.py';s=importlib.util.spec_from_file_location('vendor_followup_probe_source',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
a=m.admitted();print(json.dumps(dict(status=a['status'],whole_backend_sha256=a['whole_backend_sha256'],prerequisite=a['prerequisite'],fresh_DB_cases=0)))

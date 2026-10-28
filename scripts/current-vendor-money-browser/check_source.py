from pathlib import Path
import importlib.util,json
p=Path(__file__).resolve().parent/'probe.py';s=importlib.util.spec_from_file_location('vendor_money_browser_source',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
a=m.admitted();print(json.dumps(dict(status=a['status'],prerequisite=a['prerequisite'],fresh_browser_cases=0)))

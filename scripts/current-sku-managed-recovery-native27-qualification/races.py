"""Load the complete declared private race derivative actually used by runner."""
from pathlib import Path
import importlib.util
_path=Path(__file__).resolve().with_name('derive.py')
_spec=importlib.util.spec_from_file_location('sku27_private_races',_path)
_module=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_module)
_module.execute('races',globals())

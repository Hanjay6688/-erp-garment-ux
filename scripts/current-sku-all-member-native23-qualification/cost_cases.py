"""Private whole retained module; exact reversible adapters in derive.py."""
from pathlib import Path as _Path
import importlib.util as _importlib
_path = _Path(__file__).resolve().with_name("derive.py")
_spec = _importlib.spec_from_file_location("sku23_private_deriver", _path)
_private = _importlib.module_from_spec(_spec)
_spec.loader.exec_module(_private)
_private.execute('cost_cases', globals())

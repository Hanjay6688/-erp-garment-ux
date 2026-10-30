"""Whole retained module; explicit reversible adapters in derive.py."""
from pathlib import Path
import importlib.util
_path=Path(__file__).resolve().with_name("derive.py")
_spec=importlib.util.spec_from_file_location("sku27_private_browser_guard",_path)
_module=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_module)
_module.execute("browser_guard",globals())

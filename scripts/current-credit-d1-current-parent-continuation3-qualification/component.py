"""Private old component with one exact business factory routing change."""
from pathlib import Path as _Path
import importlib.util as _util

_here = _Path(__file__).resolve().parent
_root = _here.parents[1]
_old = _root / 'scripts/current-credit-d1-owner-followup-qualification/component.py'
_spec = _util.spec_from_file_location('d1_cont_current_component_deriver', _here / 'derive.py')
_helper = _util.module_from_spec(_spec); _spec.loader.exec_module(_helper)
_code, PRIVATE_COMPONENT_DERIVATION = _helper.component(_old.read_bytes())
# These are this new private module's globals, never an imported module patch.
exec(compile(_code, str(_old), 'exec'), globals())

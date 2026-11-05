"""Full current source admission for real browser journeys; no DB operation."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('current_browser_whole_source_binding', HERE / 'browser_binding.py')
binding = importlib.util.module_from_spec(spec);spec.loader.exec_module(binding)


def check():
    binding.entry.actual_inputs()
    with binding.scope() as (engine, source, fixture):
        pass  # Binding is complete under the fence; never invoke fixture.main.
    raw = binding.entry.admission.canonical(source)
    return dict(source, complete_source_sha256=sha256(raw).hexdigest(),
                database_calls=0,
                real_case_success_not_implied=True)


if __name__ == '__main__':
    print(json.dumps(check(), sort_keys=True, default=str))

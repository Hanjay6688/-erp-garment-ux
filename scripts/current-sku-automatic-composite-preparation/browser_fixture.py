"""Real Native setup/readback entry, closed until actual current admission."""
from pathlib import Path
from contextlib import ExitStack
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('current_browser_owning_fixture_binding', HERE / 'browser_binding.py')
binding = importlib.util.module_from_spec(spec);spec.loader.exec_module(binding)
deadline = binding.load('current_browser_separate_phase_deadlines', HERE / 'browser_deadline.py')


def main():
    binding.entry.actual_inputs()
    values = list(sys.argv[1:])
    binding.require(len(values) == 1 and values[0] in ('prepare', 'observe', 'block_inverse', 'release_inverse'),
                    'CURRENT_SKU_FIXED_NATIVE_BROWSER_OPERATION_REQUIRED')
    with ExitStack() as stack:
        with deadline.phase('SOURCE'):
            engine, source, module = stack.enter_context(binding.scope())
        with binding.arguments(values), deadline.phase('OPERATION'):
            value = module.main()
    print(json.dumps(value, sort_keys=True, default=str))


if __name__ == '__main__':
    main()

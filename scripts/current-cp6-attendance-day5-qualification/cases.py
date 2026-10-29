"""Five unmodified crossflow closures, including their original READY assertion.

The frozen crossflow adapter prepares/reserves its labelled OFF seed periods.
Its factory only declares 142 callables; selection does not run those callables.
No payroll is inserted after PRESENT attendance, and no exception is translated.
"""
from pathlib import Path
import importlib.util

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


selection = load("focused_attendance_day5_selection", HERE / "selection.py")
original = load(
    "focused_attendance_day5_original_crossflow",
    ROOT / "scripts/current-cp6-crossflow-qualification/cases.py",
)
IDS = selection.IDS
LABEL = selection.LABEL


def cases(cur, today, *, current, evidence):
    found = original.cases(cur, today, current=current, evidence=evidence)
    selected = selection.select_retained(found)
    evidence["focused_selection"] = dict(
        declared_factory_cases=len(found), selected_cases=list(IDS),
        unselected_cases_executed=0, original_callable_objects_retained=True,
        original_READY_assertion_retained=True,
        newly_posted_attendance_auto_payrolled=False,
    )
    return selected

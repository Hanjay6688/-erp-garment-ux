"""Exact retained report byte/log copier, with the same Original file names."""
from pathlib import Path
import importlib.util


if __name__ == '__main__':
    path = Path(__file__).resolve().parents[1] / 'current-credit-e1-native-qualification/retain_reports.py'
    spec = importlib.util.spec_from_file_location('e1_current_exact_raw_report_retention', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.retain(Path('cp6-proof/t3'))

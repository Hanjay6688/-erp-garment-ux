"""Call the unchanged exact Original byte retainer; no report reconstruction."""
from pathlib import Path
import importlib.util

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


if __name__=='__main__':
    path=ROOT/'scripts/current-attendance-choice-reader-native14-qualification/retain_reports.py'
    spec=importlib.util.spec_from_file_location('s03_lawful_unchanged_Original_retainer',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.retain(ROOT/'cp6-proof/t3')

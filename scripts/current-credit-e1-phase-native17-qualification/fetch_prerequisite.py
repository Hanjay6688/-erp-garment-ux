"""Full current source before GET; retain exact qualified D1 five Originals."""
from pathlib import Path
from types import ModuleType
import importlib.util
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


def main():
    load('e_phase_before_any_GET_gate',HERE/'gate.py').selected(json.loads((HERE/'CONFIG.json').read_bytes()))
    load('e_phase_before_any_GET_complete_source',HERE/'source_check.py').check()
    path=ROOT/'scripts/current-credit-e1-native-qualification/fetch_prerequisite.py'
    text,proof=load('e_phase_five_raw_derivation',HERE/'derive.py').fetch(path.read_bytes())
    m=ModuleType('e_phase_private_five_raw_fetch'); m.__file__=str(HERE/'fetch_prerequisite.py')
    exec(compile(text,str(path),'exec'),m.__dict__)
    m.main()


if __name__=='__main__':main()

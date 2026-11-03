"""Use the owning candidate's unchanged identity recorder for its package.

Inherited ERP modules keep their actual frozen paths. Only this provenance
module is selected explicitly: the unchanged recorder reports its own Git
checkout and the original GitHub job fields, without rewriting an outcome.
"""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
import importlib.util,sys

ROOT=Path(__file__).resolve().parents[2]
FROZEN=ROOT.parent/'qualified-afui-parent'
PATH='scripts/cp6_run_identity.py'
PIN=dict(bytes=1869,sha256='4876539c2ed0cffc674522f2a24ae73f2f52253f434bf949a53a3744018f2279')


def require(value,message):
    if not value:raise ValueError(message)


def source():
    for root in(ROOT,FROZEN):
        path=root/PATH;require(path.is_file()and not path.is_symlink(),'MANDOR_IDENTITY_REGULAR_PINNED_SOURCE_REQUIRED')
        raw=path.read_bytes()
        require(dict(bytes=len(raw),sha256=sha256(raw).hexdigest())==PIN,'MANDOR_IDENTITY_UNCHANGED_RECORDER_REQUIRED')
    require((ROOT/PATH).read_bytes()==(FROZEN/PATH).read_bytes(),'MANDOR_IDENTITY_EXACT_INHERITED_SOURCE_REQUIRED')
    return dict(path=PATH,source=PIN,recorder_uses_owning_checkout=True,
        inherited_ERP_modules_or_outcomes_relabelled=False,actual_Native_cases=0)


@contextmanager
def scope():
    proof=source()
    spec=importlib.util.spec_from_file_location('mandor_owning_package_identity',ROOT/PATH)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    require(module.ROOT.resolve()==ROOT.resolve(),'MANDOR_IDENTITY_OWNING_CHECKOUT_REQUIRED')
    sentinel=object();previous=sys.modules.get('cp6_run_identity',sentinel)
    sys.modules['cp6_run_identity']=module
    try:yield proof
    finally:
        if previous is sentinel:sys.modules.pop('cp6_run_identity',None)
        else:sys.modules['cp6_run_identity']=previous

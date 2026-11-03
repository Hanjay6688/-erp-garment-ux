"""Prepared bridge to the actual current parent, with no acceptance on import.

No old SKU27 receipt or reduced catalogue is manufactured. The complete
Mandor/Afui parent is verified before child DDL and after the narrow inverse.
Actual composite transactions and the complete outer restore remain mandatory.
"""
from hashlib import sha256
import inspect
import json
import os
from pathlib import Path
import subprocess
from types import ModuleType
import sku_current_parent_admission as admission
import sku_current_parent_derive as derive

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FROZEN_SKU = ROOT.parent / "qualified-sku-moving-average"
FROZEN_PARENT = ROOT.parent / "qualified-mandor-parent"
EXPECTED_PARENT_MODULE = FROZEN_PARENT / "scripts/current-mandor-shop-native-qualification/assembly.py"


def require(value, message):
    if not value:
        raise ValueError(message)


def source_manifest():
    raw = (HERE / "SOURCE.json").read_bytes()
    manifest = json.loads(raw)
    require(manifest['contract']=='cp7.current-mandor-SKU-parent-bridge-preparation.v1',
            'SKU_COMPOSITE_EXACT_SOURCE_CONTRACT')
    names=('PARENT_HEAD','PARENT_TREE','PARENT_ROOT_PIN','PARENT_SOURCE_PIN','PARENT_MODULE_PIN',
           'SKU_HEAD','SKU_TREE','SKU_ROOT_PIN','SKU_SOURCE_PIN','RUNTIME_ENTRY')
    unset=[getattr(admission,name)is None for name in names]
    require(all(unset)or not any(unset),'SKU_COMPOSITE_NO_PARTIAL_ADMISSION')
    require(manifest['actual_parent_adopted']is(not any(unset))
            and manifest['all_admission_values_unset']is all(unset)
            and type(manifest['actual_composite_cases'])is int and manifest['actual_composite_cases']==0
            and manifest['production_go']is False,
            'SKU_COMPOSITE_UNQUALIFIED_SOURCE_AND_ACTUAL_PARENT_GATE_STATE')
    if not any(unset):
        require(manifest['source_SKU_candidate']==admission.SKU_HEAD
                and manifest['source_SKU_tree']==admission.SKU_TREE
                and manifest['source_SKU_actual_Native6_acceptance']is True,
                'SKU_COMPOSITE_MANIFEST_EXACT_ACCEPTED_CHILD')
    for name, reference in manifest["files"].items():
        path = HERE / name
        require(path.is_file() and not path.is_symlink() and admission.pin(path.read_bytes()) == reference,
                "SKU_COMPOSITE_PREPARED_SOURCE_CHANGED:" + name)
    return admission.pin(raw)


def load_prepared(parent, sku_module, parent_raw, sku_raw):
    # This refusal precedes all module inspection, Git access, and ERP imports.
    receipt = admission.admitted(parent_raw, sku_raw)
    own = source_manifest()
    require(Path(inspect.getfile(type(parent))).resolve() == EXPECTED_PARENT_MODULE.resolve(),
            "SKU_COMPOSITE_EXACT_CURRENT_MANDOR_ASSEMBLY_REQUIRED")
    require(admission.pin(EXPECTED_PARENT_MODULE.read_bytes()) == admission.PARENT_MODULE_PIN,
            "SKU_COMPOSITE_EXACT_ACCEPTED_CURRENT_PARENT_ASSEMBLY_SOURCE_REQUIRED")
    expected = FROZEN_SKU / "scripts/cp7_sku_moving_average"
    require(Path(sku_module.__file__).resolve() == expected / "composition.py",
            "SKU_COMPOSITE_EXACT_FROZEN_CHILD_MODULE_REQUIRED")
    for name in ("private_delta", "consumer_delta", "reader_delta", "credit_delta", "catalog_additions", "reader_access"):
        require(Path(getattr(sku_module, name).__file__).resolve() == expected / (name + ".py"),
                "SKU_COMPOSITE_EXACT_FROZEN_CHILD_DEPENDENCY_REQUIRED:" + name)
    env = dict(os.environ, GIT_NO_LAZY_FETCH="1")
    def git(*args):
        return subprocess.check_output(["git", "-C", str(FROZEN_SKU), *args], env=env)
    require(git("rev-parse", "HEAD").decode().strip() == admission.SKU_HEAD,
            "SKU_COMPOSITE_FROZEN_CHILD_HEAD_CHANGED")
    require(git("rev-parse", "HEAD^{tree}").decode().strip() == admission.SKU_TREE,
            "SKU_COMPOSITE_FROZEN_CHILD_TREE_CHANGED")
    require(not git("status", "--porcelain", "--untracked-files=no").strip(),
            "SKU_COMPOSITE_FROZEN_CHILD_SOURCE_DIRTY")
    raw = (expected / "composition.py").read_bytes()
    code, derivation = derive.derive(raw)

    def bridge_sources():
        require(admission.admitted(parent_raw, sku_raw) == receipt and source_manifest() == own,
                "SKU_COMPOSITE_ADMISSION_OR_SOURCE_CHANGED")
        require(admission.pin(EXPECTED_PARENT_MODULE.read_bytes()) == admission.PARENT_MODULE_PIN,
                "SKU_COMPOSITE_CURRENT_PARENT_ASSEMBLY_SOURCE_CHANGED")
        require(admission.pin(admission.canonical(parent.sources())) == admission.PARENT_SOURCE_PIN,
                "SKU_COMPOSITE_COMPLETE_CURRENT_PARENT_SOURCE_GRAPH_CHANGED")
        require(admission.pin(admission.canonical(sku_module.sources())) == admission.SKU_SOURCE_PIN,
                "SKU_COMPOSITE_COMPLETE_ACCEPTED_CHILD_SOURCE_GRAPH_CHANGED")
        return dict(receipt=receipt, preparation_source=own, derivation=derivation,
                    parent_state_projection=False, actual_composite_cases=0)

    bridge_sources()
    module = ModuleType("sku_current_mandor_composition")
    module.__file__ = str(expected / "composition.py")
    module.__package__ = sku_module.__package__
    module._CURRENT_PARENT = parent
    module._BRIDGE_SOURCES = bridge_sources
    exec(compile(code, module.__file__ + ":current-parent-bridge", "exec"), module.__dict__)
    return module

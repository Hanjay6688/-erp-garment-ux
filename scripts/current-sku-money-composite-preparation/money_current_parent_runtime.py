"""Unarmed owning current-parent SKU qualifier; no ERP work on import.

The complete accepted Mandor and SKU worktrees keep their original source
fences. Only this new qualifier owns the result files and package identity.
All ten Root/source/entry gates must be populated from actual accepted runs.
"""
from pathlib import Path
from types import ModuleType
import argparse,importlib.util,json,os,subprocess,sys
from money_execution_bindings import admission,assembly,package_derivation,component,retained_arguments

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FROZEN_PARENT=assembly.FROZEN_PARENT
FROZEN_SKU=assembly.FROZEN_SKU
FROZEN_AFUI=ROOT.parent/'qualified-afui-parent'
ENTRY='scripts/current-sku-money-composite-preparation/money_current_parent_runtime.py'
BRANCH='refs/heads/astra-a/sku-current-parent-money-native19-20261104'
LABEL='CP7_SKU_CURRENT_PARENT_MONEY_QUALIFICATION'
PARENT_FILE=HERE/'MANDOR17_PARENT_ROOT_ACTUAL_INTAKE.json'
SKU_FILE=HERE/'SKU_MONEY_PREPARED_SOURCE_INTAKE.json'


def require(value,message):
    if not value:raise ValueError(message)


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def actual_inputs():
    # No file access, module inspection or Git before the actual Mandor Root and exact candidate source gates.
    admission.require_ready()
    require(admission.RUNTIME_ENTRY==ENTRY,'SKU_COMPOSITE_EXACT_OWNING_RUNTIME_ENTRY_REQUIRED')
    parent_raw=PARENT_FILE.read_bytes();sku_raw=SKU_FILE.read_bytes()
    receipt=admission.admitted(parent_raw,sku_raw,assembly.prepared_sources()[0]['native_case_ids'])
    return parent_raw,sku_raw,receipt


def frozen(root,head,tree):
    env=dict(os.environ,GIT_NO_LAZY_FETCH='1')
    def git(*args):return subprocess.check_output(['git','-C',str(root),*args],env=env,text=True).strip()
    require(root.is_dir()and not root.is_symlink(),'SKU_COMPOSITE_EXACT_FROZEN_DIRECTORY')
    require(git('rev-parse','HEAD')==head and git('rev-parse','HEAD^{tree}')==tree,
        'SKU_COMPOSITE_EXACT_FROZEN_HEAD_AND_TREE')
    require(not git('status','--porcelain','--untracked-files=no'),'SKU_COMPOSITE_FROZEN_TRACKED_SOURCE_CHANGED')


@retained_arguments()
def runtime():
    parent_raw,sku_raw,receipt=actual_inputs()
    assembly.source_manifest()
    frozen(FROZEN_PARENT,admission.PARENT_HEAD,admission.PARENT_TREE)
    frozen(FROZEN_SKU,admission.SKU_HEAD,admission.SKU_TREE)
    qualifier=FROZEN_PARENT/'scripts/current-mandor-shop-native-qualification'
    # The frozen parent uses its original inert module names. Refuse another
    # qualifier in this process instead of replacing already imported modules.
    for name in ('admission','assembly','component','package_engine','package_identity','advisor_review'):
        existing=sys.modules.get(name)
        if existing is not None:
            require(Path(existing.__file__).resolve()==qualifier/(name+'.py'),
                'SKU_COMPOSITE_INHERITED_MODULE_COLLISION:'+name)
    sys.path.insert(1,str(qualifier))
    parent_entry=load('sku_exact_accepted_Mandor_qualifier',qualifier/'qualification.py')
    parent_engine=parent_entry.runtime()
    with parent_engine.inherited_admission.parent_scope():
        parent_proof=parent_engine.admitted()
        existing=sys.modules.get('cp7_sku_cost_components')
        if existing is not None:
            require(Path(existing.__file__).resolve()==FROZEN_SKU/'scripts/cp7_sku_cost_components/__init__.py',
                'SKU_COMPOSITE_CHILD_PACKAGE_COLLISION')
        sys.path.insert(1,str(FROZEN_SKU/'scripts'))
        from cp7_sku_cost_components import composition as accepted_child
        product=assembly.load_prepared(parent_engine.product,accepted_child,parent_raw,sku_raw)
        original=FROZEN_PARENT/package_derivation.ORIGINAL
        text,package_proof=package_derivation.derive(original.read_bytes())
        engine=ModuleType('current_parent_SKU_whole_package');engine.__file__=str(original)
        exec(compile(text,engine.__file__+':current-SKU','exec'),engine.__dict__)
        engine.product=product
        engine.runner,component_proof=component.load_prepared(assembly,product,parent_raw,sku_raw,parent_engine.runner.scheduler_quiet)
        engine.trusted_installer_connection=parent_engine.trusted_installer_connection
        # Keep all inherited Afui/Mandor authority findings on their exact
        # accepted reviewer; the old generic private-work reviewer is invalid.
        engine.current_advisor=parent_engine.current_advisor
        engine.IDS=(component.CASE,);engine.LABEL=LABEL;engine.REPO=ROOT
        engine.PRE_DUMP='/tmp/current_parent_sku_money_native19_pre.dump'
        engine.OUT=ROOT/'cp6-proof/t3'/(LABEL+'.json')
        engine.inherited_admission=parent_engine.inherited_admission
        def admitted():
            require(actual_inputs()==(parent_raw,sku_raw,receipt),'SKU_COMPOSITE_ORIGINAL_ROOT_BYTES_CHANGED')
            frozen(FROZEN_PARENT,admission.PARENT_HEAD,admission.PARENT_TREE)
            frozen(FROZEN_SKU,admission.SKU_HEAD,admission.SKU_TREE)
            fence=load('money_current_parent_owning_source_fence',HERE/'check_source.py').check()
            return dict(status='ACTUAL_MANDOR17_MONEY19_SOURCES_ADMITTED_CURRENT_PARENT_RUN_STILL_REQUIRED',
                receipt=receipt,owning_source=fence,parent_source=parent_engine.admitted(),
                complete_combined_sources=product.sources(),whole_engine=package_proof,component=component_proof,
                actual_composite_cases=0,fresh_Auth_HTTP_or_browser_or_race_claim=False,
                production_go=False,independent_acceptance=False)
        engine.admitted=admitted
        engine.prepared_parent_proof=parent_proof
    return engine


def main():
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check',action='store_true');mode.add_argument('--runtime',action='store_true');args=parser.parse_args()
    actual_inputs()
    require(os.environ.get('GITHUB_REF')==BRANCH,'SKU_COMPOSITE_SINGLE_OWNING_BRANCH')
    require(os.environ.get('SKU_CURRENT_PARENT_MONEY_CONFIRM')=='cp6_rollback','SKU_COMPOSITE_EXPLICIT_DISPOSABLE_CONFIRMATION')
    if args.check:
        fence=load('money_current_parent_original_import_DB_fence',
            FROZEN_AFUI/'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
        with fence.fenced_source_read()as guard:
            engine=runtime()
            with engine.inherited_admission.parent_scope():proof=engine.admitted()
        print(json.dumps(dict(source=proof,source_DB_guard=guard,actual_SQL_executed=0)));return
    attempts=load('money_current_parent_original_real_WIB_policy',FROZEN_AFUI/'scripts/current-de-free-date-preparation/attempt_policy.py')
    attempts.require_window();engine=runtime()
    identity=load('money_current_parent_owning_identity',ROOT/'scripts/current-mandor-shop-native-qualification/package_identity.py')
    with engine.inherited_admission.parent_scope():
        engine.admitted();import cp6_auditor_business_day as business_day
        old_runtime=engine.package._writer_runtime;old_output=engine.package.OUT
        try:
            engine.package._writer_runtime=lambda browser_mode=False:engine.run()
            engine.package.OUT=ROOT/'cp6-proof/t3'
            with identity.scope(),attempts.single_attempt(business_day):engine.package.run('install')
        finally:engine.package._writer_runtime=old_runtime;engine.package.OUT=old_output


if __name__=='__main__':main()

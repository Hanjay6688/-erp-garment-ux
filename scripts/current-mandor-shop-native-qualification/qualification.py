"""Single owning package entry; actual accepted-parent gate remains closed.

There is no database connection, installation or case dispatch on import. The
unchanged owning package engine performs full backup/restore and role cleanup;
only its documented writer-runtime slot supplies this new component.
"""
from pathlib import Path
from types import ModuleType
from urllib.parse import urlparse
import argparse,importlib.util,json,os,subprocess,sys
import admission

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FROZEN=ROOT.parent/'qualified-afui-parent'
PARENT_FILE=HERE/'AFUI15_PARENT_ROOT_ACTUAL_INTAKE.json'
BRANCH='refs/heads/astra-a/mandor-shop-native9-on-unified-20261103'


def require(value,message):
    if not value:raise ValueError(message)


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module


def actual_parent():
    require(admission.PARENT_ROOT_PIN is not None and admission.RUNTIME_ENTRY is not None,
        'MANDOR_NATIVE_ACTUAL_AFUI15_ROOT_ACCEPTANCE_AND_OWNING_CALLER_PENDING')
    require(admission.RUNTIME_ENTRY=='scripts/current-mandor-shop-native-qualification/qualification.py',
        'MANDOR_NATIVE_EXACT_OWNING_ENTRY_REQUIRED')
    raw=PARENT_FILE.read_bytes();return raw,admission.parent(raw)


def runtime():
    raw,parent=actual_parent()  # Before any ERP graph or database import.
    require(FROZEN.is_dir(),'MANDOR_NATIVE_EXACT_FROZEN_AFUI_WORKTREE_REQUIRED')
    require(subprocess.check_output(['git','-C',str(FROZEN),'rev-parse','HEAD'],text=True).strip()==admission.PARENT_HEAD,
        'MANDOR_NATIVE_EXACT_FROZEN_AFUI_HEAD')
    # Keep this qualifier's directory first for its own inert modules. Every
    # inherited ERP module comes from the complete, accepted Afui worktree.
    for path in [str(ROOT/'scripts'),str(FROZEN/'scripts')]:
        if path not in sys.path:sys.path.insert(1,path)
    existing=sys.modules.get('cp7_accessory_nonpayable')
    if existing is not None:
        require(Path(existing.__file__).resolve()==FROZEN/'scripts/cp7_accessory_nonpayable/__init__.py',
            'MANDOR_NATIVE_ANOTHER_AFUI_PACKAGE_ALREADY_LOADED')
    from cp7_accessory_nonpayable import admission as inherited_admission
    with inherited_admission.parent_scope():
        engine=runtime_inherited(raw,parent)
    engine.inherited_admission=inherited_admission
    return engine


def runtime_inherited(raw,parent):
    from cp7_mandor_shop import composition as mandor
    require(Path(mandor.__file__).resolve()==ROOT/'scripts/cp7_mandor_shop/composition.py',
        'MANDOR_NATIVE_CURRENT_MANDOR_MODULE_REQUIRED')
    from cp7_accessory_nonpayable import assembly as afui,native_fixture as physical
    import assembly,component,package_engine,package_identity,advisor_review
    product=assembly.Assembly(afui,physical,mandor,raw)
    original=FROZEN/package_engine.ORIGINAL
    text,engine_proof=package_engine.derive(original.read_bytes())
    engine=ModuleType('writer_a_mandor_exact_whole_package_engine');engine.__file__=str(original)
    exec(compile(text,str(original),'exec'),engine.__dict__)

    def trusted_connection():
        # Only the installation transaction and used-inverse inspection use
        # this pre-existing disposable maintenance authority. Normal Native
        # cases and committed payment keep the original ordinary PG connector.
        uri=os.environ.get('CP6_ADMISSION_CONTROL_PGURL','');parsed=urlparse(uri)
        require(parsed.hostname=='127.0.0.1'and parsed.port==54322 and parsed.path=='/template1'
            and parsed.username=='cp6_maintenance_admission'and not parsed.query and not parsed.fragment,
            'MANDOR_NATIVE_FIXED_LOCAL_MAINTENANCE_ONLY')
        import psycopg
        connection=psycopg.connect(uri,dbname='cp6_rollback')
        try:
            with connection.cursor()as cursor:
                require(cursor.execute('select current_database()').fetchone()==('cp6_rollback',),'MANDOR_NATIVE_FIXED_INSTALL_DATABASE')
                mandor.trusted_installer(cursor)
        except BaseException:
            connection.close();raise
        return connection

    engine.product=product;engine.runner=component.runner(product,trusted_connection)
    engine.current_advisor=advisor_review
    engine.IDS=(component.CASE,);engine.LABEL=component.LABEL
    engine.REPO=ROOT;engine.PRE_DUMP='/tmp/current_mandor_native9_full_pre.dump'
    engine.OUT=ROOT/'cp6-proof/t3'/(component.LABEL+'.json')
    engine.trusted_installer_connection=trusted_connection
    def admitted():
        actual_parent()
        fence=load('writer_a_current_unified_source_fence',ROOT/'scripts/current-unified-candidate/check_source.py').source()
        return dict(status='ACTUAL_AFUI15_PARENT_AND_UNIFIED_MANDOR_CALLER_SOURCE_ADMITTED',parent=parent,
            complete_sources=product.sources(),unified_source_fence=fence,whole_engine_derivation=engine_proof,
            owning_package_identity_source=package_identity.source(),
            owning_advisor_source=advisor_review.source(),
            actual_Native_cases=0,actual_Auth_HTTP_cases=0,actual_browser_cases=0,production_go=False,independent_acceptance=False)
    engine.admitted=admitted
    return engine


def main():
    p=argparse.ArgumentParser();mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check',action='store_true');mode.add_argument('--runtime',action='store_true');args=p.parse_args()
    actual_parent()
    require(os.environ.get('GITHUB_REF')==BRANCH,'MANDOR_NATIVE_SINGLE_OWNING_BRANCH')
    require(os.environ.get('MANDOR_NATIVE_CONFIRM')=='cp6_rollback','MANDOR_NATIVE_EXPLICIT_DISPOSABLE_CONFIRMATION')
    if args.check:
        fence=load('mandor_exact_original_import_DB_fence',FROZEN/'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
        with fence.fenced_source_read()as guard:
            engine=runtime()
            with engine.inherited_admission.parent_scope():proof=engine.admitted()
        print(json.dumps(dict(source=proof,source_DB_guard=guard,actual_SQL_executed=0)));return
    attempts=load('mandor_unchanged_genuine_six_hour_WIB_policy',FROZEN/'scripts/current-de-free-date-preparation/attempt_policy.py')
    attempts.require_window();engine=runtime()
    with engine.inherited_admission.parent_scope():
        engine.admitted()
        import cp6_auditor_business_day as business_day
        original=engine.package._writer_runtime;original_output=engine.package.OUT
        try:
            engine.package._writer_runtime=lambda browser_mode=False:engine.run()
            # Only the artifact destination moves to the owning candidate;
            # the original package and complete backup drill remain exact.
            engine.package.OUT=ROOT/'cp6-proof/t3'
            import package_identity
            with package_identity.scope(),attempts.single_attempt(business_day):engine.package.run('install')
        finally:
            engine.package._writer_runtime=original;engine.package.OUT=original_output


if __name__=='__main__':main()


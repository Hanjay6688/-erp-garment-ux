"""Complete actual public52eed first, then preserved242/currentAC source readers."""
from pathlib import Path
from types import ModuleType
import importlib.util
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OLD=ROOT/'scripts/current-s05-current-ac-editor-qualification'


def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def historical():
    raw=(OLD/'admission.py').read_bytes()
    text,proof=load('s05_wib_owner_counted_source_reader',HERE/'derive.py').admission(raw)
    m=ModuleType('s05_wib_owner_private_current_AC_source_reader');m.__file__=str(OLD/'admission.py')
    m.__S05_WIB_OWNER_FULL_SOURCE_SCOPE__=lambda repo:load('s05_wib_owner_actual_public_scope',HERE/'source_check.py').check(repo=repo)
    exec(compile(text,str(OLD/'admission.py'),'exec'),m.__dict__)
    return m,proof


def offline(repo=ROOT,here=HERE):
    repo,here=Path(repo),Path(here)
    current=load('s05_wib_owner_complete_source_first',here/'source_check.py').check(repo=repo,here=here)
    old,derivation=historical()
    inherited=old.offline(repo,repo/'scripts/current-s05-current-ac-editor-qualification')
    failure=load('s05_wib_owner_exact_failed10_negative',here/'first_failure.py').check(repo,here)
    cfg=json.loads((here/'CONFIG.json').read_bytes())
    if inherited['source_files']!=242 or inherited['current_AC_premise']['current_prosrc_sha256']!='3f468d69475ebd199c7a0af7b4ee4486e6b71a5287a0ee63ac0e3dac24f15364':
        raise ValueError('S05_WIB_OWNER_EXACT_HISTORICAL242_CURRENT_AC_REQUIRED')
    return dict(status='S05_WIB_OWNER_PREPARED_SOURCE_ONLY_FRESH_FULL10_REQUIRED',
        source_qualification=json.loads((here/'SOURCE.json').read_bytes()),
        source_files=current['source_pins'],Native_case_ids=inherited['Native_case_ids'],
        complete_public_source=current,historical_current_AC_source=inherited,
        private_source_scope_derivation=derivation,retained_52eed_negative=failure,
        accepted_fresh_native10=cfg['accepted_fresh_native10'],
        original_ten_callbacks_money_qty_dates_and_Native_guards_unchanged=True,
        actual_Native_credit=0,database_calls=0,production_go=False,independent_acceptance=False)

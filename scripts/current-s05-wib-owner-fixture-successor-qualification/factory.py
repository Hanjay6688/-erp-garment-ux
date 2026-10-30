"""Reuse complete currentAC/lawful recipe; scope only two private fixture helpers."""
from pathlib import Path
from hashlib import sha256
import importlib.util

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CURRENT=ROOT/'scripts/current-s05-current-ac-editor-qualification'


def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def business(retained,state):
    private=load('s05_wib_owner_frozen_current_AC_factory',CURRENT/'factory.py').business(retained,state)
    adapter=load('s05_wib_owner_private_fixture_adapter',HERE/'fixture_adapter.py').FixtureAdapter(private,state)
    original_cases=private.cases
    private.fixture=adapter.fixture
    private.issue_note=adapter.issue_note
    def cases(cur,today,parent):
        selected=original_cases(cur,today,parent)
        if [name for name,_ in selected]!=list(retained.IDS):raise ValueError('S05_UNCHANGED_ORIGINAL_TEN_IDS_REQUIRED')
        def scoped(name,operation):
            def run():
                with adapter.case_scope(name):return operation()
            return run
        return [(name,scoped(name,operation)if name in ('S05_NATIVE_WIB_COHORTS','S05_NATIVE_CURRENT_ACCESS_PRIVATE_ACL')else operation)
                for name,operation in selected]
    private.cases=cases
    private.wib_owner_fixture_adapter=adapter
    private.wib_owner_derivation=dict(original_callback_source_SHA256=sha256((ROOT/'scripts/cp7_accessory_standard_report/cases.py').read_bytes()).hexdigest(),
        raw_callback_body_substitutions=0,private_case_scope_wrappers=2,private_dependency_bindings=['fixture','issue_note'],
        original_imported_module_mutated=False,all_ten_original_money_quantity_and_date_cohort_assertions_unchanged=True,
        retained_current_AC_recipe_unchanged=True,Native_case_credit=0)
    return private

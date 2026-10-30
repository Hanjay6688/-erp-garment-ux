"""Counted private qualification readers only; all original sources stay exact."""
from hashlib import sha256


def replace(raw,changes,label):
    text=raw.decode()
    for before,after in changes:
        if text.count(before)!=1:raise ValueError('S05_WIB_OWNER_EXACT_ANCHOR_REQUIRED:'+label)
        text=text.replace(before,after,1)
    reversed_text=text
    for before,after in reversed(changes):
        if reversed_text.count(after)!=1:raise ValueError('S05_WIB_OWNER_UNIQUE_REVERSE_ANCHOR_REQUIRED:'+label)
        reversed_text=reversed_text.replace(after,before,1)
    if reversed_text.encode()!=raw:raise ValueError('S05_WIB_OWNER_DERIVATION_NOT_EXACT_REVERSE:'+label)
    return text,dict(original_sha256=sha256(raw).hexdigest(),derived_sha256=sha256(text.encode()).hexdigest(),
        counted_changes=len(changes),reverse_original_bytes_exact=True,classification=label)


def admission(raw):
    return replace(raw,(
        ('module.__S05_CURRENT_AC_SUCCESSOR_SCOPE__ = tracked_scope',
         'module.__S05_CURRENT_AC_SUCCESSOR_SCOPE__ = __S05_WIB_OWNER_FULL_SOURCE_SCOPE__'),
        ('tracked_scope=tracked_scope(repo)',
         'tracked_scope=__S05_WIB_OWNER_FULL_SOURCE_SCOPE__(repo)'),
    ),'TWO_HISTORICAL_SCOPE_READER_ROUTES_AFTER_COMPLETE_PUBLIC52EED_CLOSURE')


def probe(raw):
    return replace(raw,(
        ("admission = load('s05_current_AC_source_before_imports', HERE/'admission.py')",
         "admission = load('s05_current_AC_source_before_imports', __S05_WIB_OWNER_HERE__/'admission.py')"),
        ("factory = load('s05_current_AC_only_private_recipe_factory', HERE/'factory.py')",
         "factory = load('s05_current_AC_only_private_recipe_factory', __S05_WIB_OWNER_HERE__/'factory.py')"),
        ('all_original_ten_financial_callbacks_assertions_and_dates_unchanged=True,',
         'all_original_ten_callback_bytes_financial_assertions_and_WIB_date_cohorts_unchanged=True,\n                supported_WIB_seconds_fixture_transition_disclosed=True,'),
        ("                new_Native_function_rewrites=0, actual_editor_observations_are_not_financial_case_credit=True,",
         "                wib_owner_fixture_derivation=private.wib_owner_derivation if private else None,\n                actual_wib_owner_fixture_observations=private.wib_owner_fixture_adapter.observations if private else [],\n                new_Native_function_rewrites=0, actual_editor_observations_are_not_financial_case_credit=True,"),
    ),'TWO_PRIVATE_SOURCE_FACTORY_ROUTES_PLUS_TWO_HONEST_FIXTURE_PROVENANCE_BLOCKS')

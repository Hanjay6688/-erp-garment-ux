"""Bound the old fixture premise to the exact qualified AC editor source."""
from hashlib import sha256
from pathlib import Path
from types import ModuleType
import importlib.util
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT/'scripts/current-s05-lawful-master-dates-qualification'
AC = 'supabase/release/cp6-t3/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql'
AC_SHA = '871fb32b1d4a1e7f9aedfef684b0f2c766092732c38552620eb394061f6240d1'
OLD_RECIPE_SHA = '0740c5e18470d8fe2fcd9115887b63e7804fad12a6ab4213840f539bccf07262'
OLD_BODY_SHA = '6c8c701395ab74874e7cb2f3e78f9912f7380a5a3199cba069b1aec6db09cd85'
CURRENT_BODY_SHA = '3f468d69475ebd199c7a0af7b4ee4486e6b71a5287a0ee63ac0e3dac24f15364'
EDITOR = 'erp.save_accessory_bom_edit(uuid,jsonb,timestamp with time zone,text)'
OLD_EXPRESSION = "to_char(v_eff,'YYYYMMDD-HH24MI')"
CURRENT_EXPRESSION = "to_char((v_eff AT TIME ZONE 'Asia/Jakarta'),'YYYYMMDD-HH24MI')"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


def editor_definition(text):
    matches = list(re.finditer(r'CREATE OR REPLACE FUNCTION erp\.save_accessory_bom_edit\(', text))
    if len(matches) != 1:
        raise ValueError('S05_AC_EXACT_ONE_EDITOR_DEFINITION_REQUIRED')
    tail = text[matches[0].start():]
    dollar = re.search(r'\bAS\s+(\$[A-Za-z_0-9]*\$)', tail)
    end = tail.index(dollar[1], dollar.end())
    return tail[:end+len(dollar[1])+1]+'\n', tail[dollar.end():end]


def premise(repo=ROOT):
    repo = Path(repo)
    raw = (repo/AC).read_bytes()
    if sha256(raw).hexdigest() != AC_SHA:
        raise ValueError('S05_EXACT_CURRENT_AC_MIGRATION_REQUIRED')
    definition, current = editor_definition(raw.decode())
    old_path = repo/'scripts/current-s05-lawful-master-dates-qualification/native-premise/save_accessory_bom_edit.sql'
    _, old = editor_definition(old_path.read_text())
    if (sha256(old.encode()).hexdigest() != OLD_BODY_SHA or old.count(OLD_EXPRESSION) != 1
            or old.replace(OLD_EXPRESSION, CURRENT_EXPRESSION, 1) != current
            or sha256(current.encode()).hexdigest() != CURRENT_BODY_SHA):
        raise ValueError('S05_EXACT_ONE_WIB_LABEL_SOURCE_TRANSITION_REQUIRED')
    return definition, dict(status='EXACT_CURRENT_AC_SOURCE_PREMISE_NOT_RUNTIME_CAPTURE',
        migration=AC, migration_sha256=AC_SHA, old_prosrc_sha256=OLD_BODY_SHA,
        current_prosrc_sha256=CURRENT_BODY_SHA, counted_WIB_label_expression_changes=1,
        all_other_Native_editor_body_bytes_equal=True, Native_function_rewrites=0,
        actual_current_catalog_capture=False, actual_Native_credit=0)


def current_recipe(raw):
    """Only the historical helper's exact ABI constant changes privately."""
    anchor = "EDITOR_BODY_SHA256 = '"+OLD_BODY_SHA+"'"
    replacement = "EDITOR_BODY_SHA256 = '"+CURRENT_BODY_SHA+"'"
    if sha256(raw).hexdigest() != OLD_RECIPE_SHA or raw.count(anchor.encode()) != 1:
        raise ValueError('S05_FROZEN_LAWFUL_RECIPE_ABI_ANCHOR_REQUIRED')
    result = raw.replace(anchor.encode(), replacement.encode(), 1)
    if result.replace(replacement.encode(), anchor.encode(), 1) != raw:
        raise ValueError('S05_CURRENT_ABI_TRANSITION_NOT_REVERSIBLE')
    module = ModuleType('s05_private_current_AC_recipe')
    module.__file__ = str(OLD/'recipe.py')
    exec(compile(result, module.__file__, 'exec'), module.__dict__)
    return module, dict(original_sha256=OLD_RECIPE_SHA, derived_sha256=sha256(result).hexdigest(),
        counted_ABI_constant_changes=1, initial_editor_and_BF_successor_code_otherwise_byte_exact=True)


def admit_editor(cur, state, observations):
    """Actual current row plus actual installed parent, before fixture writes."""
    actual = cur.execute("select pg_get_functiondef(p.oid),pg_get_userbyid(p.proowner),encode(sha256(convert_to(p.prosrc,'UTF8')),'hex') from pg_proc p where p.oid=%s::regprocedure", (EDITOR,)).fetchone()
    expected = state['after']['functions'][EDITOR]
    row = dict(kind='ACTUAL_CURRENT_INSTALLED_EDITOR_ABI_OBSERVATION', signature=EDITOR,
        observed_tuple=list(actual) if actual is not None else None,
        observed_definition_sha256=sha256(actual[0].encode()).hexdigest() if actual else None,
        observed_owner=actual[1] if actual else None, observed_prosrc_sha256=actual[2] if actual else None,
        installed_parent_definition_sha256=sha256(expected[0].encode()).hexdigest(),
        installed_parent_owner=expected[1], admitted=False, Native_case_credit=0)
    observations.append(row)
    if (actual is None or tuple(actual[:2]) != tuple(expected[:2]) or actual[1] != 'postgres'
            or expected[1] != 'postgres' or actual[2] != CURRENT_BODY_SHA):
        raise ValueError('S05_EXACT_CURRENT_AC_INSTALLED_EDITOR_AND_OWNER_REQUIRED')
    row['admitted'] = True
    return row

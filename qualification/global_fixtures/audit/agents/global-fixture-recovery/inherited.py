"""Closed source routes for the three original Nota cases and Global advisors."""

import ast
from importlib import import_module
import json
from pathlib import Path
from types import SimpleNamespace

from foundation import pin, require


NOTE = 'scripts/cp7_note_correction_cases.py'
NOTE_PIN = '1f6bfff2974b865d54600dec4fd515bd8b931efdd737c19e50eb8b1a094f604c'
NOTE_IDS = ('NOTE_PREPAYMENT_REPLAY', 'NOTE_PREPAYMENT_OVERPAYMENT_ATOMIC', 'NOTE_OLD_ADVANCE_CASH_REPORT')
NOTE_ZONES = ('Asia/Jakarta', 'UTC')
SCHEMA = 'cp7_global_nonpo_envelope'
TABLES = tuple(f'{SCHEMA}.{name}' for name in ('profiles', 'scope_completions_v1', 'work_scopes_v1'))
ADVISOR_SQL = 'scripts/current-sku-automatic-composite-preparation/advisor_review.py'
ADVISOR_SOURCES = {
    ADVISOR_SQL: 'f95d7be158f86a644111105dfd12a2a45581be015dc381f3cfa598c89ce802f8',
    f'scripts/{SCHEMA}/schema.sql': '9cbb6f3c9d167e77c80e6c1047e4e497cf03bf10b7f59e839465a2c6cdaa56bd',
    f'scripts/{SCHEMA}/work_scope.sql': 'fd379bef9aac477d77a5d7aa74a7d7ed32f9217f38d95a9af9f6c9e9f7b5505c',
}
PRIVILEGES = ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER')
PUBLIC_ROLES = ('anon', 'authenticated', 'service_role')
COLUMN_AND_CREATE_SQL = """
select w, r, has_any_column_privilege(r,to_regclass(w),'SELECT,INSERT,UPDATE,REFERENCES'),
       has_schema_privilege(r,%s,'CREATE')
from unnest(%s::text[]) w cross join unnest(%s::text[]) r
order by w collate "C", r collate "C"
"""


def checked(candidate, relative, expected):
    path = candidate / relative
    require(path.is_file() and not any(part.is_symlink() for part in (path, *path.parents)),
            'GLOBAL_INHERITED_REGULAR_SOURCE_REQUIRED:' + relative)
    raw = path.read_bytes()
    require(pin(raw)['sha256'] == expected, 'GLOBAL_INHERITED_EXACT_SOURCE_REQUIRED:' + relative)
    return raw


def bind_nota(candidate, roots, report_io):
    raw = checked(candidate, NOTE, NOTE_PIN)
    module = import_module('cp7_note_correction_cases')
    path = Path(module.__file__).absolute()
    require(any(path == root / NOTE for root in roots) and path.is_file()
            and not any(part.is_symlink() for part in (path, *path.parents)) and path.read_bytes() == raw
            and module.cases.__globals__ is module.__dict__
            and module.cases.__code__ == report_io.function_code(raw, str(path), 'cases'),
            'GLOBAL_NOTA_EXACT_RETAINED_CASE_FACTORY_REQUIRED')
    require(tuple(key for key in module.MANIFEST['groups']['native'] if key in NOTE_IDS) == NOTE_IDS,
            'GLOBAL_NOTA_EXACT_THREE_ORIGINAL_CASE_IDS_REQUIRED')
    return module.cases, dict(factory=pin(raw), selected=list(NOTE_IDS), session_timezones=list(NOTE_ZONES))


def run_nota(cases, runner, verify, output_scope, complete_group, require_quiet):
    reports = {}
    for zone in NOTE_ZONES:
        require_quiet()

        def factory(cur, today):
            original = [(name, callback) for name, callback in cases(cur, today) if name in NOTE_IDS]
            require(tuple(name for name, _ in original) == NOTE_IDS, 'GLOBAL_NOTA_EXACT_SELECTED_ORIGINALS_REQUIRED')

            def in_zone(operation):
                def execute():
                    cur.execute("select set_config('TimeZone',%s,true)", (zone,))
                    result = operation()
                    require(cur.execute("select current_setting('TimeZone')").fetchone() == (zone,),
                            'GLOBAL_NOTA_ORIGINAL_TIMEZONE_CONTEXT_CHANGED')
                    return dict(result, actual_Native_session_TimeZone=zone)
                return execute

            return [(name, in_zone(operation)) for name, operation in original]

        name = 'GLOBAL_FIRST_NATIVE_NOTA_' + ('WIB' if zone == 'Asia/Jakarta' else 'UTC')
        with output_scope():
            reports[zone] = complete_group(runner.strict_group(name, factory, verify), NOTE_IDS)
        require_quiet()
    return reports


def validate_authority(proof):
    roles, tables, extra = (proof[name] for name in ('roles', 'tables', 'column_and_schema_create'))
    require(type(roles) is list and roles == sorted(set(roles)) and set(PUBLIC_ROLES) <= set(roles)
            and all(role in PUBLIC_ROLES or role.startswith('cp7_') for role in roles)
            and set(tables) == set(TABLES), 'GLOBAL_ADVISOR_EXACT_TABLES_AND_ROLE_CENSUS_REQUIRED')
    for name in TABLES:
        expected = dict(object=name.split('.'), owner='postgres', rls=True, force_rls=False, schema_owner='postgres',
                        nonowner_schema_acl=[], nonowner_table_acl=[], nonowner_column_acl=[], policies=[],
                        schema_usage=dict.fromkeys(roles, False),
                        table_privileges={role: dict.fromkeys(PRIVILEGES, False) for role in roles})
        require(json.dumps(tables[name], sort_keys=True) == json.dumps(expected, sort_keys=True),
                'GLOBAL_ADVISOR_PRIVATE_TABLE_AUTHORITY_CHANGED:' + name)
    require(len(extra) == len(TABLES) * len(roles)
            and {(table, role) for table, role, _, _ in extra} == {(table, role) for table in TABLES for role in roles}
            and all(column is False and create is False for _, _, column, create in extra),
            'GLOBAL_ADVISOR_EFFECTIVE_COLUMN_OR_SCHEMA_CREATE_PRIVILEGE')
    return proof


def bind_advisors(candidate):
    raw = {name: checked(candidate, name, expected) for name, expected in ADVISOR_SOURCES.items()}
    capture, = [ast.literal_eval(node.value) for node in ast.parse(raw[ADVISOR_SQL]).body
                if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == 'CAPTURE_SQL' for target in node.targets)]

    def capture_advisors(cur, state):
        planned = state.global_installation['plan']['tables']
        require(len(planned) == len(TABLES) and set(planned) == set(TABLES),
                'GLOBAL_ADVISOR_EXACT_INSTALLED_TABLE_PLAN_REQUIRED')
        roles = [role for role, in cur.execute(
            'select rolname::text from pg_roles where rolname=any(%s::name[]) or left(rolname,4)=%s '
            'order by rolname::text collate "C"', (list(PUBLIC_ROLES), 'cp7_')).fetchall()]
        rows = cur.execute(capture, (list(TABLES), roles)).fetchall()
        require(len(rows) == len(TABLES), 'GLOBAL_ADVISOR_COMPLETE_LIVE_AUTHORITY_ROWS_REQUIRED')
        effective = cur.execute(COLUMN_AND_CREATE_SQL, (SCHEMA, list(TABLES), roles)).fetchall()
        return validate_authority(dict(roles=roles, tables=dict(rows), column_and_schema_create=effective))

    def review_advisors(findings, authority):
        validate_authority(authority)
        reviewed = []
        for finding in findings:
            meta = finding.get('metadata') or {}
            name = f"{meta.get('schema')}.{meta.get('name')}"
            require(finding.get('name') == 'rls_enabled_no_policy' and finding.get('level') == 'INFO'
                    and meta.get('type') == 'table' and name in TABLES,
                    'GLOBAL_ADVISOR_UNRECOGNIZED_FINDING')
            reviewed.append(name)
        require(len(reviewed) == len(set(reviewed)), 'GLOBAL_ADVISOR_DUPLICATE_FINDING')
        return dict(gate=True, reviewed_global_private_info=findings, current_global_private_authority=authority)

    return SimpleNamespace(capture=capture_advisors, review=review_advisors,
                           source=dict(tables=list(TABLES), sources={name: pin(value) for name, value in raw.items()}))

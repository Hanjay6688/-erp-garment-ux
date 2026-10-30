"""New owned six-Original parent contract; no claim of a fresh11 or fresh14."""
from midnight_common import ROOT, HERE, document, read_original, digest
import midnight_gate as gate

FIVE = ('installed', 'primary_unchanged', 'backup_restore_drill', 'security_advisors', 'writer_runtime')
RESTORE = ('erp_platform_auth_schema_acl', 'all_public_catalog_members_and_row_hashes',
           'erp_public_auth_function_definitions_owners_acls')


def exact_group(group, ids):
    if (group.get('status') != 'PASS' or group.get('error')
            or group.get('counts') != {'PASS': len(ids)}
            or type(group.get('counts', {}).get('PASS')) is not int
            or group.get('planned_case_ids') != list(ids) or set(group.get('cases', {})) != set(ids)
            or group.get('complete_boundary_restored') is not True):
        raise ValueError('MIDNIGHT_EXACT_RESTORED_PARENT_GROUP_REQUIRED')
    for key, row in group['cases'].items():
        if (row.get('status') != 'PASS' or row.get('error')
                or row.get('full_boundary_restored') is not True
                or row.get('public_schema_unchanged') is not True):
            raise ValueError('MIDNIGHT_PARENT_CASE_BOUNDARY_REQUIRED:' + key)


def checked(docs, cfg, product_sources):
    parent, backend = gate.selected(cfg)
    if set(docs) != set(gate.SIX):
        raise ValueError('MIDNIGHT_SIX_UNPROJECTED_PARENT_ORIGINALS_REQUIRED')
    strict, reader, outer, package, files, drill = (docs[k] for k in gate.SIX)
    ids11, ids3 = parent['original11_ids'], parent['reader3_ids']
    if len(ids11) != 11 or len(ids3) != 3 or len(set(ids11 + ids3)) != 14:
        raise ValueError('MIDNIGHT_PARENT_EXACT11_PLUS3_IDS_REQUIRED')
    exact_group(strict, ids11)
    exact_group(reader, ids3)
    case_id = parent['outer_case_id']
    if (outer.get('status') != 'PASS' or outer.get('error') or outer.get('restore_error')
            or outer.get('qualification_commit') != parent['head']
            or outer.get('required_case_ids') != [case_id]
            or set(outer.get('committed', {})) != {case_id}
            or outer.get('actual_Native_cases') != 14
            or outer.get('required_case_ids_pass') is not True):
        raise ValueError('MIDNIGHT_ACTUAL_OUTER14_PASS_REQUIRED')
    for key in ('cp6_restored', 'baseline_full22_all_rows_all_sequences_equal',
                'baseline_advisors_equal', 'advisor_gate', 'used_guard_refused_before_DDL'):
        if outer.get(key) is not True:
            raise ValueError('MIDNIGHT_PARENT_FULL_RESTORE_REQUIRED:' + key)
    if (not set(RESTORE) <= set(outer.get('restore_components', {}))
            or any(v is not True for v in outer['restore_components'].values())
            or outer.get('baseline_role_cleanup', {}).get('baseline_roles_exact') is not True):
        raise ValueError('MIDNIGHT_PARENT_RESTORE_COMPONENTS_AND_ROLES_REQUIRED')
    component = outer['committed'][case_id]
    capture = component.get('actual_installed_capture', {})
    if (component.get('status') != 'PASS' or component.get('native') != strict
            or component.get('reader_native3') != reader
            or component.get('actual_Native_cases') != 14
            or component.get('required_Native_case_ids') != ids11 + ids3
            or component.get('both_groups_same_actual_installation') is not True
            or component.get('reader3_requires_actual_fresh_original11') is not True
            or component.get('combined_strict14_fabricated') is not False
            or len(capture.get('originals', {})) != 15 or len(capture.get('clones', {})) != 2
            or len(capture.get('actual_all22', {})) != 22
            or capture.get('source_derived_local_ABI_used') is not False):
        raise ValueError('MIDNIGHT_PARENT_BOTH_RAW_GROUPS_ACTUAL15_CAPTURE_REQUIRED')
    if (component.get('used_guard_refused_before_DDL') is not True
            or not component.get('committed_choice_and_allocation')
            or not component.get('independent_Native_pool_oracle')
            or not component.get('used_inverse_refusal_before')
            or component['used_inverse_refusal_before'] != component.get('used_inverse_refusal_after')
            or component.get('original_accrual_and_source_binding_unchanged') is not True):
        raise ValueError('MIDNIGHT_PARENT_ACTUAL_ALLOCATE_USED_WITNESS_REQUIRED')
    current = outer.get('source_declaration', {}).get('current_installation')
    if (current != product_sources or not current
            or current.get('files') != backend['runtime_files']
            or digest(product_sources) != backend['product_sources_sha256']):
        raise ValueError('MIDNIGHT_FULL_ACTUAL_PRODUCT_SOURCES_REQUIRED')
    identity = package.get('run_identity', {})
    if (identity.get('tool_head') != parent['head'] or identity.get('github_sha') != parent['head']
            or identity.get('run_id') != parent['run_id'] or identity.get('workflow') != parent['workflow']
            or identity.get('mode') != 'install' or identity.get('job') != 'p21'):
        raise ValueError('MIDNIGHT_SAME_ACTUAL_PARENT_PACKAGE_IDENTITY_REQUIRED')
    if (package.get('status') != 'ALL_STAGES_INSTALLED' or set(package.get('gate', {})) != set(FIVE)
            or any(package['gate'][k] is not True for k in FIVE)
            or package.get('writer_runtime', {}).get('status') != 'PASS'
            or package.get('primary_unchanged') is not True
            or package.get('backup_restore_drill') != 'RESTORED_IDENTICAL'
            or package.get('auth_users_before') is None
            or package['auth_users_before'] != package.get('auth_users_after')):
        raise ValueError('MIDNIGHT_PARENT_ALL5_PRIMARY_AUTH_REQUIRED')
    rows = files.get('files', [])
    if (files.get('status') != 'ALL_FILES_INSTALLED' or len(rows) != 30
            or len({row.get('key') for row in rows}) != 30
            or any(row.get('status') != 'PASS' for row in rows)):
        raise ValueError('MIDNIGHT_PARENT_ALL30_PACKAGE_FILES_REQUIRED')
    if (drill.get('status') != 'RESTORED_IDENTICAL' or not drill.get('checks')
            or any(v is not True for v in drill['checks'].values())
            or drill.get('catalog', {}).get('differ') != {}
            or drill.get('data', {}).get('differ') != {}
            or drill.get('engine', {}).get('equal') is not True):
        raise ValueError('MIDNIGHT_PARENT_COMPLETE_BACKUP_DRILL_REQUIRED')
    return dict(status='EXACT_ACCEPTED14_SIX_ORIGINALS_CURRENT7_ACTUAL15_ADMITTED',
                retained_parent_cases=14, retained_parent_reexecuted=False,
                fresh_Native_cases_before_execution=0, production_go=False, independent_acceptance=False)


def admitted(product, cfg=None, root=ROOT):
    cfg = document((HERE / 'CONFIG.json').read_bytes()) if cfg is None else cfg
    parent, _ = gate.selected(cfg)  # Before any Original read or product call.
    originals = {key: read_original(root, value) for key, value in parent['originals'].items()}
    docs = {key: value['document'] for key, value in originals.items()}
    actual = product.sources()
    return dict(proof=checked(docs, cfg, actual), documents=docs, product_sources=actual,
                original_pins=parent['originals'])

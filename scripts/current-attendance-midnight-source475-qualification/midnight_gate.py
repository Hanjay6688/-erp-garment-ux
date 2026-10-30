"""Root binds a future accepted14; failed9ac can never open this preparation."""
from midnight_common import ID, hash40
import parent_binding

CONTRACT = 'cp7.attendance-midnight-native1.v1'
CLOSED = 'MIDNIGHT_NATIVE1_CLOSED_ACTUAL_SUCCESSOR14_SIX_ORIGINALS_REQUIRED'
FAILED = '9ac9c8bd1bfb7d64a1e735067083c68acbff02ef'
SIX = ('strict11', 'reader3', 'outer14', 'package', 'files', 'drill')


def selected(cfg):
    if cfg.get('contract') != CONTRACT:
        raise ValueError('MIDNIGHT_EXACT_CONTRACT_REQUIRED')
    parent, backend = cfg.get('accepted_parent14'), cfg.get('backend_binding')
    if parent is None or backend is None:
        raise ValueError(CLOSED)
    if cfg.get('state') != 'ROOT_BOUND_ACTUAL_SUCCESSOR14':
        raise ValueError('MIDNIGHT_EXPLICIT_ROOT_REBIND_REQUIRED')
    if not isinstance(parent, dict) or not isinstance(backend, dict):
        raise ValueError('MIDNIGHT_EXACT_BINDING_OBJECTS_REQUIRED')
    if (parent.get('status') != 'ROOT_VERIFIED_NATIVE14_SIX_ORIGINALS_ALL5'
            or not hash40(parent.get('head')) or parent['head'] == FAILED
            or not hash40(parent.get('tree')) or parent.get('head') != backend.get('head')
            or parent.get('tree') != backend.get('tree')
            or parent.get('original11_ids') != cfg.get('expected_parent11_ids')
            or parent.get('reader3_ids') != cfg.get('expected_parent3_ids')
            or set(parent.get('originals', {})) != set(SIX)
            or not isinstance(parent.get('run_id'), str) or not parent['run_id'].isdigit()
            or not isinstance(parent.get('workflow'), str) or not parent['workflow']):
        raise ValueError('MIDNIGHT_ACTUAL_SUCCESSOR14_IDENTITY_REQUIRED')
    if (backend.get('runtime_files') != cfg['prepared_backend_runtime7']
            or len(backend['runtime_files']) != 7 or not backend.get('product_sources_sha256')
            or not backend.get('files') or not backend.get('source_manifest')):
        raise ValueError('MIDNIGHT_CURRENT_ACTUAL_RUNTIME7_SOURCE_BINDING_REQUIRED')
    if (cfg.get('case_ID') != ID or type(cfg.get('expected_new_Native_cases')) is not int
            or cfg.get('expected_new_Native_cases') != 1
            or cfg.get('expected_captured_originals') != 15 or cfg.get('expected_private_clones') != 2
            or cfg.get('fresh_original11_or14_rerun') is not False
            or cfg.get('production_go') is not False or cfg.get('independent_acceptance') is not False):
        raise ValueError('MIDNIGHT_EXACT_ONE_CASE_NO_RERUN_QUALIFICATION_ONLY')
    for item in parent['originals'].values():
        if (not isinstance(item, dict) or item.get('encoding') not in ('raw', 'gzip')
                or not isinstance(item.get('path'), str)
                or not item['path'].startswith('scripts/current-attendance-midnight-source475-qualification/accepted-parent14/')
                or set(item.get('stored', {})) != {'bytes', 'sha256'}
                or set(item.get('raw', {})) != {'bytes', 'sha256'}):
            raise ValueError('MIDNIGHT_EXACT_RETAINED_ORIGINAL_PIN_REQUIRED')
    parent_binding.checked(parent, backend)
    return parent, backend

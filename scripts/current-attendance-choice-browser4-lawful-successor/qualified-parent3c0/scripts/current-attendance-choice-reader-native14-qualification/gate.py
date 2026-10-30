"""Pure closed binding gate; nothing here imports ERP, connects or fetches."""
from hashlib import sha256
import json
import re

CONTRACT = 'cp7.attendance-choice-reader-native14.v1'
VENDOR = '41caaaed02c0d89b122ecf1ff221f6647141c335'
CLOSED = 'S03_NATIVE14_CLOSED_FROZEN_BACKEND_SOURCE_API_AND_VENDOR41C_REQUIRED'
PREFIXES = ('scripts/cp7_attendance_period_choice/',
            'scripts/current-attendance-period-choice-qualification/',
            'scripts/current-attendance-period-choice-readers-qualification/')


def selected(cfg):
    if cfg.get('qualification_contract') != CONTRACT:
        raise ValueError('S03_NATIVE14_EXACT_QUALIFICATION_CONTRACT_REQUIRED')
    bound, required, parent = (cfg.get(key) for key in
                              ('backend_binding', 'required_backend_source', 'required_qualified_parent'))
    if bound is None or required is None or parent is None:
        raise ValueError(CLOSED)
    if not all(isinstance(value, dict) for value in (bound, required, parent)):
        raise ValueError('S03_NATIVE14_REVIEWED_OBJECT_BINDINGS_REQUIRED')
    if (parent.get('head') != VENDOR
            or parent.get('status') != 'ROOT_VERIFIED_VENDOR41C_FOUR_ORIGINALS_AND_ALL5_GATES'
            or parent.get('retained41c') != cfg['retained41c']
            or parent.get('qualified_vendor_sources_sha256') != cfg['qualified_vendor_sources_sha256']):
        raise ValueError('S03_NATIVE14_EXACT_VENDOR41C_PARENT_REQUIRED')
    if (required.get('status') != 'ROOT_BOUND_FROZEN_PREPARED_BACKEND_SOURCE_AND_API'
            or required.get('head') != bound.get('head') or required.get('tree') != bound.get('tree')
            or required.get('source_sha256') != bound.get('source', {}).get('sha256')
            or required.get('API_sha256') != bound.get('API', {}).get('sha256')):
        raise ValueError('S03_NATIVE14_EXPLICIT_SOURCE_AND_API_REBIND_REQUIRED')
    if any(not re.fullmatch('[a-f0-9]{40}', bound.get(key, '')) for key in ('head', 'tree')):
        raise ValueError('S03_NATIVE14_PUBLIC_ALIAS_HEAD_TREE_REQUIRED')
    for key in ('source', 'API'):
        pin = bound.get(key, {})
        if (not isinstance(pin.get('path'), str) or not pin['path'].startswith(PREFIXES)
                or type(pin.get('bytes')) is not int or pin['bytes'] <= 0
                or not re.fullmatch('[a-f0-9]{64}', pin.get('sha256', ''))):
            raise ValueError('S03_NATIVE14_FROZEN_SOURCE_API_PIN_REQUIRED:' + key)
    if (not isinstance(cfg.get('runtime_files'), dict) or len(cfg['runtime_files']) != 7
            or cfg.get('expected_captured_originals') != 15 or cfg.get('expected_private_clones') != 2
            or len(cfg['original_Native11_ids']) != 11 or len(cfg['reader_Native3_ids']) != 3
            or cfg['Native_case_ids'] != cfg['original_Native11_ids'] + cfg['reader_Native3_ids']
            or len(set(cfg['Native_case_ids'])) != 14):
        raise ValueError('S03_NATIVE14_EXACT_RUNTIME7_CAPTURE15_CLONES2_AND_CASE14_REQUIRED')
    if cfg['failed_baseline']['used_as_prerequisite'] is not False:
        raise ValueError('S03_NATIVE14_FAILED9A0_CANNOT_BE_A_PREREQUISITE')
    if cfg.get('production_go') is not False or cfg.get('independent_acceptance') is not False:
        raise ValueError('S03_NATIVE14_QUALIFICATION_ONLY')
    return bound

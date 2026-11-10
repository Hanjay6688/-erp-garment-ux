"""Exact 15+2 Mandor input for the offline SKU source observer."""
from hashlib import sha256
import json


STATUS = 'ROOT_VERIFIED_CUMULATIVE_MANDOR17_ALL5_SOURCE_ONLY'
REVIEW_PIN = dict(bytes=20450, sha256='52732cb67467cb7a9ac8d814ca46b7e8bf27bde7aea5e24f82c84e2fe7dc8b12')
ASSEMBLY_PIN = dict(bytes=7427, sha256='57b814105f3dba27b4f3cdb34078335f61d053d3d3a774e25d520280d4236481')


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def prepare(review_raw):
    if pin(review_raw) != REVIEW_PIN:
        raise ValueError('SKU_EXACT_CUMULATIVE_MANDOR_REVIEW_REQUIRED')
    review = json.loads(review_raw)
    return canonical(dict(
        status=STATUS, **review['backend_source'],
        actual_Native_cases=9, actual_Native_session_cases=4, actual_Auth_HTTP_cases=2,
        actual_browser_cases=2, actual_business_cases=17, complete17_qualified=True,
        package_all_five=True, actual_outer_restore=True, prior_runs_aggregated=True,
        assembly_source=ASSEMBLY_PIN, qualified_current_Mandor_sources=review['mandor_source_graph'],
        cumulative_evidence=review, runtime_admission=False, production_go=False,
        independent_acceptance=False,
    ))


def verify(raw):
    root = json.loads(raw)
    if type(root) is not dict:
        raise ValueError('SKU_EXACT_CUMULATIVE_MANDOR_ROOT_REQUIRED')
    review = (json.dumps(root.get('cumulative_evidence'), sort_keys=True, indent=2) + '\n').encode()
    if prepare(review) != raw:
        raise ValueError('SKU_EXACT_CUMULATIVE_MANDOR_ROOT_REQUIRED')
    return root


def expected_parent(root):
    return {name: root[name] for name in (
        'status', 'head', 'tree', 'actual_Native_cases', 'actual_Native_session_cases',
        'actual_Auth_HTTP_cases', 'actual_browser_cases', 'actual_business_cases',
        'complete17_qualified', 'package_all_five', 'actual_outer_restore', 'prior_runs_aggregated',
        'assembly_source', 'runtime_admission', 'production_go', 'independent_acceptance',
    )}

"""Derive the exact installed report through its existing official installers.

The old diagnostic pinned the pre-install Native body. Preserve it as evidence,
then apply precisely the existing note lifecycle and R5-02 account transforms.
No live normalization, missing-function acceptance or alternate body is allowed.
"""
from pathlib import Path
from hashlib import sha256
import json,sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import cp7_note_report_bundle as notes
import cp7_report_accounts_bundle as accounts


def body(definition):
    parts=definition.split('$$')
    if len(parts)!=3 or parts[2]!=';':raise ValueError('COMPOSED_SNAPSHOT_DEFINITION_SHAPE_CHANGED')
    if not parts[0].startswith('CREATE FUNCTION erp.get_owner_financial_snapshot_v2('):
        raise ValueError('COMPOSED_SNAPSHOT_SIGNATURE_CHANGED')
    return parts[1]


def expected():
    source=json.loads((HERE/'COMPOSED_SNAPSHOT_SOURCE.json').read_bytes())
    native=json.loads((HERE/'NATIVE_SNAPSHOT_SOURCE.json').read_bytes())
    definition=(HERE/'original-snapshot-definition.sql').read_text()
    if sha256(definition.encode()).hexdigest()!=source['definition_sha256']:
        raise ValueError('COMPOSED_SNAPSHOT_NATIVE_DEFINITION_CHANGED')
    original=body(definition)
    if (original!=(HERE/'original-snapshot-body.sql').read_text()
        or sha256(original.encode()).hexdigest()!=native['body_sha256']
        or native['body_sha256']!=source['base_body_sha256']):
        raise ValueError('COMPOSED_SNAPSHOT_NATIVE_BODY_CHANGED')
    for path,digest in source['transformers'].items():
        if sha256((ROOT/path).read_bytes()).hexdigest()!=digest:
            raise ValueError('COMPOSED_SNAPSHOT_OFFICIAL_TRANSFORMER_CHANGED:'+path)
    installed=accounts.wrap(notes.SIGNATURE,notes.patched_report(definition))
    value=body(installed)
    if (len(value.encode())!=source['installed_body_bytes']
        or sha256(value.encode()).hexdigest()!=source['installed_body_sha256']):
        raise ValueError('COMPOSED_SNAPSHOT_DERIVATION_CHANGED')
    if (value.count('cp7_note.report_lifecycle(')!=2
        or value.count('cp7_sales_return_correction.report_lifecycle(')!=1
        or value.count('(select erp.account_id(')!=11):
        raise ValueError('COMPOSED_SNAPSHOT_INSTALLED_TRANSFORMS_MISSING')
    return value,source

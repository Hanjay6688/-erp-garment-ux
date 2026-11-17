"""Apply the reviewed Laundry delta to the already verified SKU parent."""

from dataclasses import dataclass
from hashlib import sha256

import dated_source_stage as dated


SOURCE_PINS = {
    'dated_source.sql': '33b7ca6b0078a5f634b71b36e9d4ebf47fedc5ad34d8272b7b4bbd70a30c02e1',
    'dated_source_stage.py': 'f9f2daf80db0d2a5413682a461d676283b17d3d7d557f0334ae0d9ba89c1319f',
}


@dataclass(frozen=True)
class Installed:
    before: dict
    after: dict
    data: dict
    original_identity: dict
    installed_identity: dict


def verify_source():
    for name, expected in SOURCE_PINS.items():
        source = dated.HERE / name
        dated.require(source.is_file() and not source.is_symlink()
                      and sha256(source.read_bytes()).hexdigest() == expected,
                      'S02_SKU_EXACT_QUALIFIED_SOURCE_REQUIRED:' + name)


def install_delta(cur, provider, verified_parent):
    """Use the SKU parent's owning transaction and the original S02 DDL."""
    verify_source()
    dated.require(verified_parent.get('status') == 'GLOBAL_ACTUAL_PARENT_CATALOGUE_AND_CENSUS_VERIFIED',
                  'S02_SKU_VERIFIED_LIVE_PARENT_REQUIRED')
    with provider.atomic(cur), provider.metadata_context(cur):
        provider.trusted_installer(cur)
        before = provider.capture(cur)
        dated.require(provider.fingerprint(cur, before) == verified_parent['live_fingerprint'],
                      'S02_SKU_PARENT_CHANGED_AFTER_LIVE_VERIFICATION')
        functions = provider.all22(before)['functions']
        dated.require(not functions.keys() & set(dated.HELPERS), 'S02_SKU_HELPERS_ALREADY_INSTALLED')
        for signature, digest in dated.PREIMAGES.items():
            row = functions[signature]
            dated.require(sha256(row[0].encode()).hexdigest() == digest and row[18] == dated.OWNER_ACL,
                          'S02_SKU_VENDOR_PREIMAGE_CHANGED:' + signature)
        data = provider._timezone_snapshot(cur, lock=False)
        original_identity = dated.native_identity(cur, dated.PREIMAGES)
        with provider.as_role(cur, 'postgres'):
            cur.execute(dated.sql_source(), prepare=False)
            cur.execute('revoke all on function ' + ','.join(dated.HELPERS) + ' from ' + dated.PRIVATE_GRANTEES)
            cur.execute(dated.apply_body(functions[dated.APPLY][0]), prepare=False)

        after = provider.capture(cur)
        dated.verify_transition(provider.all22(before), provider.all22(after))
        dated.require(all(after[key] == rows for key, rows in before.items() if key != 'functions'),
                      'S02_SKU_NON_FUNCTION_CATALOGUE_CHANGED')
        identity = dated.native_identity(cur, dated.POSTIMAGES)
        dated.require(all(identity[name] == row for name, row in original_identity.items())
                      and provider._timezone_snapshot(cur, lock=False) == data,
                      'S02_SKU_INSTALL_CHANGED_DATA_SEQUENCE_OR_AUTHORITY')
        return Installed(before, after, data, original_identity, identity)


def restore_preuse(cur, provider, state):
    """Restore the raw SKU parent only while the dated child is still unused."""
    with provider.atomic(cur), provider.metadata_context(cur):
        provider.trusted_installer(cur)
        dated.require(provider.capture(cur) == state.after
                      and dated.native_identity(cur, dated.POSTIMAGES) == state.installed_identity,
                      'S02_SKU_CHILD_CATALOGUE_OR_AUTHORITY_CHANGED')
        dated.require(provider._timezone_snapshot(cur, lock=True) == state.data,
                      'S02_SKU_USED_DELTA_REQUIRES_BACKUP_RESTORE')
        originals = dict(state.before['functions'])
        with provider.as_role(cur, 'postgres'):
            for signature in dated.PREIMAGES:
                cur.execute(originals[signature][0], prepare=False)
            for signature in reversed(dated.HELPERS):
                cur.execute('drop function ' + signature + ' restrict')
        dated.require(provider.capture(cur) == state.before
                      and dated.native_identity(cur, dated.PREIMAGES) == state.original_identity
                      and provider._timezone_snapshot(cur, lock=False) == state.data,
                      'S02_SKU_PREUSE_INVERSE_DID_NOT_RESTORE_PARENT')

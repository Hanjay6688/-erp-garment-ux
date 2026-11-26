"""Derive the Enteng OW04 trigger manifest from the reviewed installment source."""
from copy import deepcopy

import cp7_enteng_managed_identity as identity


def declarations(guard, repo):
    manifest = deepcopy(guard.declarations(repo))
    signature = 'cp7_installment.guard_journal()'
    role, expected_hash = identity.PINS[signature]
    for phase in manifest['phases'].values():
        candidates = [item for item in phase['functions'] if item['identity']==signature]
        if len(candidates)!=1:
            raise ValueError('Expected one installment journal guard in each OW04 phase')
        item = candidates[0]
        source = item['source_definition']
        parts = source.split('$$')
        if (len(parts)!=3 or item['owner']!=role or item['definition_sha256'] is not None
                or identity.digest(parts[1])!=expected_hash or item['body_sha256']!=expected_hash
                or identity.digest(source)!=item['source_definition_sha256']
                or source not in (repo/item['source']).read_text()):
            raise ValueError('Unexpected canonical installment guard')
        body, count = identity.IDENTITY_CALL.subn(lambda m: 'cp7_request_context.' + m[1].lower() + '()', parts[1])
        if count!=1:
            raise ValueError('Expected exactly one private identity binding')
        parts[1]=body
        item['source_definition']='$$'.join(parts)
        item['source_definition_sha256']=identity.digest(item['source_definition'])
        item['body_sha256']=identity.digest(body)
    return manifest

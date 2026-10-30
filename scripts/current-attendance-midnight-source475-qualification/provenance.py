"""Check immutable c097 history and every counted active routing substitution."""
from midnight_common import HERE, ROOT, document, pin, regular


def substitute(raw, pairs):
    value = raw.decode()
    for item in pairs:
        if item['count'] != 1 or value.count(item['before']) != 1:
            raise ValueError('MIDNIGHT_ONE_EXACT_ROUTING_ANCHOR_REQUIRED')
        value = value.replace(item['before'], item['after'], 1)
    restored = value
    for item in reversed(pairs):
        if restored.count(item['after']) != 1:
            raise ValueError('MIDNIGHT_ONE_EXACT_REVERSE_ROUTING_ANCHOR_REQUIRED')
        restored = restored.replace(item['after'], item['before'], 1)
    if restored.encode() != raw:
        raise ValueError('MIDNIGHT_ALL_UNCHANGED_C097_BYTES_REQUIRED')
    return value.encode()


def check(root=ROOT, here=HERE):
    retained = document((here / 'RETAINED_C097.json').read_bytes())
    if (retained.get('head') != 'c0975ead5c9ff5e0677a2b7b9a86ef9cd3b37db5'
            or len(retained.get('files', {})) != 41
            or retained.get('historical_only') is not True
            or retained.get('actual_producer') is not False
            or retained.get('actual_Git_root') is not False):
        raise ValueError('MIDNIGHT_EXACT41_C097_HISTORICAL_FILES_REQUIRED')
    for name, expected in retained['files'].items():
        stored = here / 'retained-c097' / name
        relative = str(stored.relative_to(root))
        if pin(regular(root, relative).read_bytes()) != expected:
            raise ValueError('MIDNIGHT_C097_HISTORY_CHANGED:' + name)
    derived = document((here / 'DERIVATIONS.json').read_bytes())
    for item in derived['active_routes']:
        original = regular(root, str((here / 'retained-c097' / item['original_path']).relative_to(root))).read_bytes()
        actual = regular(root, item['path']).read_bytes()
        if pin(original) != item['original'] or pin(actual) != item['derived']:
            raise ValueError('MIDNIGHT_ACTIVE_ROUTE_HASH_CHANGED:' + item['path'])
        if substitute(original, item['counted_replacements']) != actual:
            raise ValueError('MIDNIGHT_UNDECLARED_ACTIVE_ROUTE:' + item['path'])
    return dict(retained_c097_files=41, active_counted_routes=len(derived['active_routes']),
                historical_files_are_not_active_producers=True, product_changes=0)

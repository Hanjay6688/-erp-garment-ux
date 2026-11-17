"""Derive the pending Global worker's source without starting the worker."""

from hashlib import sha256
from pathlib import Path
from types import FunctionType


FIRST_GLOBAL_WRITER_SHA = '224406a2dba2ec0a3c13edb1a3a328599e315abaf256ea2d80f4df63474110c6'
COMPOSED_PATCH_SHA = '43383d3ea504963d55a8d1c66f3ba30cc7748e559eab0d70ae5b1e5e0dfb8ecc'


def compose_writer(source, foundation, cleanup, expected_patch):
    """Compose the existing reviewed routes and match the independently retained patch."""
    from difflib import unified_diff

    if sha256(source.encode()).hexdigest() != FIRST_GLOBAL_WRITER_SHA:
        raise ValueError('GLOBAL_OWNING_EXACT_SOURCE_WRITER_REQUIRED')
    with_auth, _ = cleanup.derive(source)
    combined, _ = foundation.derive(with_auth, ((foundation.COMMIT, foundation.AFTER_COMMIT),))
    patch = ''.join(unified_diff(source.splitlines(keepends=True), combined.splitlines(keepends=True),
                                 'retained/global_owning_writer.py', 'proposal/global_owning_writer.py'))
    if (patch.encode() != expected_patch or sha256(expected_patch).hexdigest() != COMPOSED_PATCH_SHA):
        raise ValueError('GLOBAL_OWNING_REVIEWED_FOUNDATION_AUTH_COMPOSITION_CHANGED')
    return combined


def private_auth_package(routes, engine, lifecycle, runner, report_io, sku_source, combined, candidate, attempt, error_code):
    """Reuse the existing private writer view with the one owning Auth attempt."""
    if attempt is None or not all(callable(getattr(attempt, method, None))
                                   for method in ('begin', 'before_restore', 'after_restore')):
        raise ValueError('GLOBAL_OWNING_REVIEWED_AUTH_ATTEMPT_REQUIRED')
    if not callable(error_code):
        raise ValueError('GLOBAL_OWNING_EXACT_AUTH_ERROR_ROUTE_REQUIRED')
    owner = routes.bind(engine, lifecycle, runner, report_io, sku_source, combined, candidate)
    namespace = owner.run_inner.__globals__
    if owner.run.__globals__ is not namespace or namespace is engine.__dict__ or '_global_auth' in namespace:
        raise ValueError('GLOBAL_OWNING_ISOLATED_WRITER_NAMESPACE_REQUIRED')
    namespace.update(_global_auth=attempt, _global_auth_error=error_code)
    return owner

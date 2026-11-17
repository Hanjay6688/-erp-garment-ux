"""Bind the retained transfer-page case to the existing owning connector."""

from hashlib import sha256
from pathlib import Path
import sys
from types import ModuleType

from psycopg.pq import TransactionStatus


PAGE = 'nov13-recovery/global-ow06-page-source/ow06_transfer_page.py'
OBSERVER = 'agents/global-transfer-race-proof/race_observer.py'
PAGE_SHA = 'b6797d23a855a82344986f76359dcfaa01f7328b4f27bc8f974135b348c1657b'
OBSERVER_SHA = '865393d5b0dae025067eda927053b065658c3295c9617ab4b5adb366aec77f63'
LOGIN = 'cp6_maintenance_admission'
STARTUP_IDENTITY = 'select current_user, session_user, pg_current_xact_id_if_assigned() is null'
ROUTES = (
    ('        return connection\n\n    require_quiet()',
     '        return _finish_trusted_startup(connection)\n\n    require_quiet()'),
    ('        def read(cur):\n            return workspace(cur, cases, fixture, 0, raw)\n',
     '        def read(cur):\n'
     '            return _restore_observer_identity(cur, workspace(cur, cases, fixture, 0, raw))\n'),
)


def require(condition, label):
    if not condition:
        raise ValueError(label)


def exact(path, digest):
    path = Path(path).absolute()
    require(path.is_file() and not path.is_symlink(), 'OW06_TRANSFER_PAGE_REGULAR_SOURCE_REQUIRED')
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == digest, 'OW06_TRANSFER_PAGE_SOURCE_PIN_CHANGED:' + path.name)
    return raw


def finish_trusted_startup(connection):
    """End only the read-only identity checks in the fresh trusted factory."""
    try:
        status = connection.info.transaction_status
        if status == TransactionStatus.INTRANS:
            require(not connection.autocommit
                    and connection.execute(STARTUP_IDENTITY).fetchone() == (LOGIN, LOGIN, True),
                    'OW06_TRANSFER_PAGE_FRESH_NO_XID_MAINTENANCE_STARTUP_REQUIRED')
            connection.rollback()
        require(connection.info.transaction_status == TransactionStatus.IDLE,
                'OW06_TRANSFER_PAGE_FRESH_IDLE_CONNECTION_REQUIRED')
        return connection
    except BaseException:
        connection.close()
        raise


def restore_observer_identity(cur, response):
    """Restore the connection login after the inherited Native actor helper."""
    cur.execute('RESET SESSION AUTHORIZATION')
    return response


def derived_page(raw):
    original = source = raw.decode()
    for before, after in ROUTES:
        require(source.count(before) == 1 and after not in source, 'OW06_TRANSFER_PAGE_ROUTE_CHANGED')
        source = source.replace(before, after, 1)
    restored = source
    for before, after in reversed(ROUTES):
        require(restored.count(after) == 1, 'OW06_TRANSFER_PAGE_EXACT_INVERSE_REQUIRED')
        restored = restored.replace(after, before, 1)
    require(restored == original, 'OW06_TRANSFER_PAGE_ORIGINAL_BYTES_NOT_RECOVERED')
    return source


def bind(audit):
    """Prepare the archived callback and preserve admission in its exercise entry."""
    audit = Path(audit).absolute()
    observer_path = audit / OBSERVER
    observer = ModuleType('race_observer')
    observer.__file__ = str(observer_path)
    exec(compile(exact(observer_path, OBSERVER_SHA), observer.__file__, 'exec', dont_inherit=True), vars(observer))
    page_path = audit / PAGE
    page = ModuleType('ow06_transfer_page')
    page.__file__ = str(page_path)
    vars(page).update(_finish_trusted_startup=finish_trusted_startup,
                      _restore_observer_identity=restore_observer_identity)
    raw = exact(page_path, PAGE_SHA)
    previous = sys.modules.get('race_observer')
    sys.modules['race_observer'] = observer
    try:
        exec(compile(derived_page(raw), page.__file__, 'exec', dont_inherit=True), vars(page))
    finally:
        if previous is None:
            del sys.modules['race_observer']
        else:
            sys.modules['race_observer'] = previous
    require(page.observe is observer.observe and page.idle is observer.idle,
            'OW06_TRANSFER_PAGE_EXACT_PRIVATE_OBSERVER_REQUIRED')
    return page

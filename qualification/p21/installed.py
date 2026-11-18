"""Installed evidence adapters for the focused P21 follow-up."""

from .s06_followup import CHECKS, exercise, proven, require


def verify_loopback(conn, cur):
    info = conn.info
    require(cur.connection is conn and not conn.autocommit and info.host in ('localhost', '127.0.0.1')
            and info.port == 54322 and info.dbname == 'cp6_rollback'
            and info.transaction_status.name == 'IDLE',
            'CP7_P21_DISPOSABLE_LOOPBACK_CLONE_REQUIRED')

"""Full read census and explicit admin access fixture on one disposable copy."""
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse
import gzip
import importlib.util
import json
import os
import re
import sys
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ('observe', 'deactivate_admin', 'reactivate_admin'):
        raise ValueError('S05_SKU_BROWSER_FIXTURE_OPERATION_REQUIRED')
    operation, args = sys.argv[1], json.load(sys.stdin)
    if os.environ.get('S05_SKU_BROWSER_CONFIRM') != 'cp6_auditor_browser':
        raise ValueError('S05_SKU_EXPLICIT_DISPOSABLE_BROWSER_REQUIRED')
    url = os.environ['AUDITOR_BROWSER_DB_URL']; parsed = urlparse(url)
    if parsed.hostname not in ('127.0.0.1', 'localhost') or parsed.port != 54322 or parsed.path != '/cp6_auditor_browser':
        raise ValueError('S05_SKU_BROWSER_COPY_ONLY')
    spec = importlib.util.spec_from_file_location('s05_sku_browser_fresh_source', HERE/'persistent_source.py')
    source = importlib.util.module_from_spec(spec); spec.loader.exec_module(source)
    source.preflight()
    saved = sys.argv
    try:
        sys.argv = sys.argv[:1]; sys.path.insert(0, str(ROOT/'scripts'))
        import psycopg
        from cp7_accessory_standard_report import cases as fixtures
        from cp7_s05_s03_sku_composition import stage
        from cp7_p21_current_chain_rehearsal_probe import helper
    finally:
        sys.argv = saved
    state_raw = (ROOT/'cp6-proof/t3/S05_PERMANENT_BROWSER_READER_STATE.json').read_bytes()
    if sha256(state_raw).hexdigest() != os.environ['S05_SKU_BROWSER_READER_STATE_SHA256']:
        raise ValueError('S05_SKU_ORIGINAL_READER_STATE_CHANGED')
    state = json.loads(state_raw)
    with psycopg.connect(url, connect_timeout=10) as conn, conn.cursor() as cur:
        if cur.execute('select current_database()').fetchone() != ('cp6_auditor_browser',):
            raise ValueError('S05_SKU_ACTUAL_COPY_DATABASE_REQUIRED')
        cur.execute("set local statement_timeout='90s';set local lock_timeout='8s'")
        with helper.control.product_catalog(cur):
            stage.verify(cur, state)
        if operation == 'observe':
            label = args['label']
            if not re.fullmatch(r'S05_SKU_(DESKTOP|MOBILE390)_[A-Z0-9_]+', label):
                raise ValueError('S05_SKU_BOUND_EVIDENCE_LABEL_REQUIRED')
            catalog = stage.parent().runtime()[-1]
            rows, data = catalog._catalog_rows(cur), catalog._data(cur)
            if len(rows) != 22:
                raise ValueError('S05_SKU_ALL22_REQUIRED')
            raw = (json.dumps(dict(catalog_rows=rows, data_and_sequences=data), sort_keys=True, default=str)+'\n').encode()
            target = ROOT/'cp6-proof/t3'/(label+'_FULL_CURRENT_STATE.json.gz')
            packed = gzip.compress(raw, mtime=0); target.write_bytes(packed)
            conn.rollback()
            return dict(catalog_groups=22, catalog_sha256=catalog.digest(rows),
                data_and_sequences=data, dropped_catalog_fields=[], dropped_data_or_sequence_keys=[],
                raw_evidence=dict(name=target.name, bytes=len(raw), sha256=sha256(raw).hexdigest(),
                                  gzip_bytes=len(packed), gzip_sha256=sha256(packed).hexdigest()))
        subject = str(uuid.UUID(args['auth_user_id']))
        before = cur.execute("select u.id::text,u.auth_user_id::text,u.role,r.role_code,u.is_active "
            "from erp.app_users u join erp.app_roles r on r.id=u.role_id where u.auth_user_id=%s for update of u", (subject,)).fetchall()
        wanted = operation == 'reactivate_admin'
        if len(before) != 1 or tuple(before[0][2:4]) != ('ADMIN', 'ADMIN') or before[0][4] is wanted:
            raise ValueError('S05_SKU_EXACT_REAL_AUTH_ADMIN_TRANSITION_REQUIRED')
        fixtures.b.api.admin(cur)
        cur.execute('update erp.app_users set is_active=%s where id=%s', (wanted, before[0][0]))
        after = cur.execute('select id::text,auth_user_id::text,role,is_active from erp.app_users where id=%s', (before[0][0],)).fetchone()
        if after[3] is not wanted or after[0:3] != before[0][0:3]:
            raise ValueError('S05_SKU_ADMIN_ACCESS_TRANSITION_NOT_EXACT')
        conn.commit()
        return dict(status='ADMINISTRATIVE_ACCESS_FIXTURE_ONLY', before=list(before[0]), after=list(after),
                    Native_financial_case_credit=0, UI_master_edit_claim=False)


if __name__ == '__main__':
    print(json.dumps(main(), default=str))

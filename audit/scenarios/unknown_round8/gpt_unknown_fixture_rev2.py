"""Known nonzero laundry/QC source on the browser's disposable copy only.
Upstream fixture uses existing native business commands, no direct quantity edit.
Temporary schema usage is restored before actual browser actors run.
"""
from datetime import date, timedelta
from decimal import Decimal
import uuid
from pathlib import Path
from urllib.parse import urlsplit
import json, os, sys
import psycopg

sys.path.insert(0, str(Path.cwd() / 'scripts'))
sys.path.append(str(Path.cwd().parent / 'auditor/scripts'))
import cp6_aw_probe as awp


def fixture(scope, today):
    url = os.environ['AUDITOR_BROWSER_DB_URL']
    assert urlsplit(url).path == '/cp6_auditor_browser'
    with psycopg.connect(url) as conn, conn.cursor() as raw:
        cur = awp.OrdinaryDraftCursor(raw)
        awp.api.admin(cur)
        before = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if not before:
            cur.execute('grant usage on schema erp to authenticated')
        awp.chain.production.prior.set_open_period(cur, today - timedelta(days=4))
        # Same real work/sewing/delivery recipe, without r1's unused extra FG SKU.
        # A GOOD-only receipt needs no new product; do not pollute lookup identities.
        chain = awp.chain
        f = chain.work.draft(cur, today, Decimal(0))
        chain.peer.ordinary(cur)
        cur.execute('select erp.post_work_completion(%s)', (f['completion'],))
        chain.production.owner(cur)
        cur.execute('select public.erp_record_sewing_terminal_v1(%s::jsonb,%s)',
                    (json.dumps(dict(work_completion_id=str(f['completion']), qty_pcs=10,
                                     reason='GPT ten physical pieces for read-recovery fixture')), uuid.uuid4()))
        awp.api.admin(cur)
        day = cur.execute("select (physical_at at time zone 'Asia/Jakarta')::date from erp.work_completion_events where id=%s", (f['completion'],)).fetchone()[0]
        batch = cur.execute('select b.id from erp.cutting_distribution_batches b join erp.cutting_pickups p on p.id=b.pickup_id where p.cutting_group_id=%s', (f['group'],)).fetchone()[0]
        f.update(batch=str(batch), group=str(f['group']), day=day)
        f['delivery'] = chain.laundry_action(cur, 'POST_DELIVERY', dict(
            distribution_batch_id=f['batch'], vendor_id=chain.base.VENDOR,
            wash_process_id=chain.base.BASE_PROCESS, target_dyeing_color='AUR1-NAVY',
            physical_at=chain.production.at(day, 11).isoformat(),
            reason='GPT ten physical pieces for read-recovery fixture',
            lines=[dict(size_id=chain.base.SIZE, qty_sent_pcs=10)]),
            chain.base.group_version(cur, f['group']))['delivery_id']
        if scope == 'QC':
            awp.r1.receipt(cur, f, awp.chain.production.at(f['day'], 13), 0)
        awp.api.admin(cur)
        if not before:
            cur.execute('revoke usage on schema erp from authenticated')
        after = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        assert before == after
        out = dict(scope=scope, delivery=str(f['delivery']), group=str(f['group']),
                   expected_source_pcs=10, schema_usage_before=before, schema_usage_after=after)
        conn.commit()
    return out


if __name__ == '__main__':
    print(json.dumps(fixture(sys.argv[1], date.fromisoformat(sys.argv[2])), default=str))

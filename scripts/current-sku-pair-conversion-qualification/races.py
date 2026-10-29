"""Prepared callbacks for the existing disposable two-session race tools.

Caller must restore its complete installed dump around each committed fixture.
These callbacks are not invoked by runner.py yet and grant no race credit.
"""
from pathlib import Path
import importlib.util,uuid

HERE=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location('sku29_race_fixture',HERE/'fixture.py')
f=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(f)
IDS=('SKU29_RACE_SAME_UUID_COMMIT_REPLAY','SKU29_RACE_DISTINCT_UUID_COMMIT_STALE','SKU29_RACE_DISTINCT_UUID_ROLLBACK_RECOVERY')

def exercise(tools,today,*,same_uuid,first_commit):
    with tools.connect()as conn,conn.cursor()as cur:
        assert conn.info.host in('localhost','127.0.0.1')and conn.info.port==54322
        assert cur.execute('select current_database()').fetchone()in(('cp6_rollback',),('cp6_auditor_race',))
        fixture=f.nonpo(cur,today);payload,_=f.review(cur,fixture['payload']);conn.commit()
    first=str(uuid.uuid4());second=first if same_uuid else str(uuid.uuid4())
    held,contention,outcome=tools.two_sessions(lambda cur:f.action(cur,'POST',payload,first),lambda cur:f.action(cur,'POST',payload,second),first_commit)
    assert contention.get('kind')=='BLOCKED'and contention.get('holder_blocks_worker')is True,contention
    with tools.connect()as conn,conn.cursor()as cur:
        assert conn.info.host in('localhost','127.0.0.1')and conn.info.port==54322
        groups=f.one(cur,'select count(*)from cp7_sku_conversion.groups_v1 where request_id=any(%s::uuid[])',[first,second])
        members=f.one(cur,'select count(*)from cp7_sku_conversion.members_v1 where group_id=any(%s::uuid[])',[first,second])
        source=f.stocks(cur,fixture['source'],fixture['location']);target=f.stocks(cur,fixture['target'],fixture['location'])
        conn.rollback()
    stale=first_commit and not same_uuid
    if stale:assert not outcome.get('ok')and 'STALE_VERSION'in(outcome.get('message')or''),outcome
    else:assert outcome.get('ok')is True,outcome
    assert groups==1 and members==2,(groups,members)
    assert source==dict(physical=6,reserved=1,available=5)and target==dict(physical=8,reserved=0,available=8),(source,target)
    return dict(status='PASS',first_commit=first_commit,same_uuid=same_uuid,holder=held,contention=contention,outcome=outcome,
      one_group_exactly_two_Native_parts=True,source=source,target=target,full_restore_required_by_caller=True)

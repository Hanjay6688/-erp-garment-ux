"""Ordinary reminder CRUD on the disposable Global with payloads captured from the exact UI."""
import json
from datetime import datetime, timedelta
from pathlib import Path
import psycopg
import cp7_r3_reminders_cases as rem
from common import db, measure_seal, save, record_failure, TODAY

def query(offset):
    return dict(filter="OPEN",limit=25,offset=offset)

def run():
    ui=json.loads(Path(__file__).with_name("reminder_ui_inputs.json").read_bytes())
    out=dict(pages=[],edits=[],phase="start")
    with psycopg.connect(**db()) as a, a.cursor() as q, psycopg.connect(**db()) as b, b.cursor() as second:
        out["seal"]=measure_seal(q)
        for n in (26,51,1):
            who=rem.owner(q)
            for i in range(n):
                rem.save(q,who,'SAVE',rem.body(rem.at_wib(TODAY,9)+timedelta(minutes=i),title=f'Cross audit {i}'))
            a.commit()
            off=(n-1)//25*25
            last=rem.get(q,who,query(off))['items']
            assert len(last)==1
            rem.save(q,who,'DONE',dict(id=last[0]['id']),expected=last[0]['row_version'])
            a.commit()
            after=rem.get(second,who,query(off))
            correct=rem.get(second,who,query(max(off-25,0)))
            expected=rem.order_of(second,who,'OPEN')
            assert after['page']['total']==len(expected)==n-1 and after['page']['shown']==0
            assert after['counts']['open']==n-1 and after['counts']['done']==1
            assert [i['id'] for i in correct['items']]==expected[max(off-25,0):max(off-25,0)+25]
            out['pages'].append(dict(initial=n,offset=off,actual=after['page'],correct=correct['page'],heading_on_original_ui=ui['pagination_'+str(n)]['heading']))
            b.commit();save('reminder-cross',out)
        who=rem.owner(q)
        for mode in ('title','note','intentional'):
            form=ui['time_'+mode];orig=form['original']
            created=rem.save(q,who,'SAVE',rem.body(orig,title='Astra clock',note=''));a.commit()
            rid=created['reminder_id'];before=rem.row(second,rid);b.commit()
            cmd=dict(form['payload'],id=rid)
            rem.save(q,who,'SAVE',cmd,expected=before['row_version']);a.commit()
            after=rem.row(second,rid)
            assert before['due_at']==datetime.fromisoformat(orig)
            assert after['due_at']==datetime.fromisoformat(cmd['due_at']) and after['row_version']==before['row_version']+1
            assert after['title']==cmd['title'] and after['note']==cmd['note']
            delta=after['due_at']-before['due_at']
            if mode in ('title','note'): assert delta==timedelta(seconds=-32,microseconds=-942069)
            out['edits'].append(dict(mode=mode,before=before['due_at'],after=after['due_at'],difference_seconds=delta.total_seconds(),title=after['title'],note=after['note']))
            b.commit();save('reminder-cross',out)
        who=rem.owner(q)
        clock=rem.at_wib(TODAY,12)
        for i in range(27):
            rem.save(q,who,'SAVE',rem.body(clock+timedelta(minutes=i),title='Cross session '+str(i)))
        a.commit()
        first=rem.get(q,who,query(0));first_ids=[x['id'] for x in first['items']]
        expected=rem.order_of(q,who,'OPEN');a.commit()
        rem.save(second,who,'DONE',dict(id=first_ids[0]),expected=first['items'][0]['row_version']);b.commit()
        more=rem.get(q,who,query(25));more_ids=[x['id'] for x in more['items']];a.commit()
        assert expected[25] not in first_ids+more_ids and more_ids==[expected[26]]
        before=[x['id'] for x in rem.get(q,who,query(0))['items']];a.commit()
        rem.save(second,who,'SAVE',rem.body(clock-timedelta(minutes=3),title='Earlier due'));b.commit()
        after=[x['id'] for x in rem.get(q,who,query(25))['items']]
        assert before[-1] in after
        out['offset_during_change']=dict(separate_connections=True,skipped_after_done=1,repeated_after_insert=1)
        out.update(phase='complete',outcome='CONFIRMED_ON_CANDIDATE')
        save('reminder-cross',out)
if __name__=='__main__':
    try: run()
    except Exception as err: record_failure('reminder-cross',err);raise

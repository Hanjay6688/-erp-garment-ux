"""Independent model arithmetic, owner yield policy and competing plan probes."""
import copy,json,math,threading,time,uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal as D
from queue import Queue
from statistics import NormalDist
import psycopg
import cp7_pl5_history_yield_cases as h
import cp7_model_native_cases as model
import cp7_p19_plan_v2_cases as v2
import cp7_plan_native_cases as v1
from cases_stage import wrap,check,save,admin,refusal


def wilson(good,cut):
    # Independent stdlib inverse normal rather than the product's constant/formula implementation.
    z=NormalDist().inv_cdf(.9);p=good/cut
    lower=(p+z*z/(2*cut)-z*math.sqrt(p*(1-p)/cut+z*z/(4*cut*cut)))/(1+z*z/cut)
    return math.floor(1000*lower)/1000

def cases(cur,today):
    def yield_policy():
        owner=h.actor(cur);p=h.product(cur,'astra-own-205');made=h.Production(cur,today)
        cuts=[39,40,41,42,43];goods=[35,39,38,40,41]
        groups=[]
        h.save(cur,h.payload(reason='Owner approved package; independent synthetic dataset only'),owner)
        for qty,good in zip(cuts,goods):
            group=made.group(p,qty,good);groups.append(group['group'])
            h.prove(cur,[group['group']])
            if len(groups)==4:
                insufficient,_=h.history(cur,p['target'],p['model'],owner)
                check(insufficient['status']=='INSUFFICIENT_SAMPLE' and insufficient['lower_bound'] is None,'Four groups162PCS remains insufficient',observed=insufficient)
        observed,_=h.history(cur,p['target'],p['model'],owner)
        expected=wilson(sum(goods),sum(cuts))
        save('AS20-24_independent_wilson',dict(cuts=cuts,goods=goods,expected=str(expected),observed=observed))
        check(D(observed['lower_bound'])==D(str(expected)),'One-sided90% Wilson lower bound floored0.1%',expected=expected,observed=observed)
        check(observed['level']=='PRODUCT_SIZE' and len(observed['proofs'])==5,'Exact product size first, all five finished groups proved',observed=observed)
        check(observed['window_days']=='180' and observed['minimum_sample']==dict(groups='5',cut_pcs='200'),'Owner policy unchanged')
        # A distinct color/root of the same model can use the model fallback, with exactly the same real production facts.
        sibling=h.product(cur,'astra-same-model')
        fallback,_=h.history(cur,sibling['target'],sibling['model'],owner)
        check(fallback['level']=='MODEL' and D(fallback['lower_bound'])==D(str(expected)),'Same-model fallback has exact independently calculated yield',observed=fallback)
        return dict(expected=expected,product=observed,same_model=fallback,threshold4=insufficient)

    def models():
        result=cur.execute("select cp7_models.predict('SES','[\"18\",\"28\"]','{\"alpha\":\"0.5\",\"initial_level\":\"8\"}',1)").fetchone()[0]
        check(D(result['forecasts'][0])==D('20.5'),'SES8→18→28 alpha.5 independent arithmetic',result=result)
        d=model.kernel_input(cur)
        for i,row in enumerate(d['series']):row['value']=str((i+1)*3+8)
        original=model.build(cur,d)
        # Change only held-out observation; model selection/training must not use it.
        changed=copy.deepcopy(d);changed['series'][-1]['value']='4321';later=model.build(cur,changed)
        check(original['selected_model_id']==later['selected_model_id'],'Holdout never selects the model')
        check(original['evaluation']['baseline']==later['evaluation']['baseline'] and original['evaluation']['challengers']==later['evaluation']['challengers'],'All training/fold metrics independent of holdout')
        check(original['evaluation']['holdout']!=later['evaluation']['holdout'],'Negative control affects held-out metric')
        late=copy.deepcopy(d);late['series'].append(dict(late['series'][1],revision='2',value='8765',known_at='2026-01-29T10:00:00.000000Z'))
        second=model.build(cur,late)
        check(original['selected_model_id']==second['selected_model_id'],'Late-known revision does not leak into earlier model choice')
        for a,b in zip([original['evaluation']['baseline']]+original['evaluation']['challengers'],[second['evaluation']['baseline']]+second['evaluation']['challengers']):
            check(a['summary']==b['summary'],'Late knowledge does not change prior evaluation summary')
            check([x['training'] for x in a['folds']]==[x['training'] for x in b['folds']],'Fold training preserves knowledge cutoff')
        return dict(evidence_scope='SYNTHETIC_PRIVATE_KERNEL_RUNTIME_NOT_PROOF_OF_NATIVE_HISTORY_PROMOTION',ses=result,original=original,holdout_mutation=later['evaluation']['holdout'])

    def live_policy():
        x=v2.single(cur,today);draft=v2.save(cur,x['payload']);before=v2.monetary_state(cur)
        v2.policy(cur,x,'PAUSED');ref=refusal(cur,lambda:v2.apply(cur,v2.action(draft)))
        check(ref['refused'] and ref['sqlstate']=='40001','Plan apply refuses after active policy paused',result=ref)
        check(v2.monetary_state(cur)==before and v2.intents(cur)==0,'Live refusal makes no monetary/stock/intent effect')
        return ref

    def live_fg():
        x=v2.single(cur,today);draft=v2.save(cur,x['payload']);gap=D(x['options']['needed_pcs']);amount=int(gap.to_integral_value(rounding='ROUND_CEILING'))+7
        v2.found_fg(cur,x,amount);state=v2.monetary_state(cur);before=v2.groups(cur)
        ref=refusal(cur,lambda:v2.apply(cur,v2.action(draft)))
        check(ref['refused'] and ref['sqlstate']=='40001','New physical FG satisfies need; old plan cannot cut excess',result=ref)
        check(v2.monetary_state(cur)==state and v2.groups(cur)==before,'Rejected plan leaves new stock and group count intact')
        return dict(new_fg=amount,original_need=str(gap),refusal=ref)

    return [wrap('AS20-24_PL5_OWN_DATA',yield_policy),wrap('AS20-20_MODEL_OWN_VECTORS',models),wrap('AS20-31_LIVE_POLICY',live_policy),wrap('AS20-31_LIVE_STOCK',live_fg)]


def races(tools,today):
    def cross_versions():
        with tools.connect() as conn,conn.cursor() as cur:
            first,second=v2.two(cur,today)
            c=int(D(first['options']['capacity_pcs']));need_a=int(D(first['options']['needed_pcs']));need_b=int(D(second['options']['needed_pcs']))
            a=min(need_a,c-1);b=c-a+1
            check(c>=2 and a>0 and b<=need_b and b<=c,'Independent capacity fixture constructible',capacity=c,need=[need_a,need_b],quantities=[a,b])
            orig=v1.analysis.capture(cur,today)
            q=dict(first['query'],run_id=orig['run_id']);o=v1.options(cur,q)
            payload=copy.deepcopy(first['payload']);payload.pop('identity_hash');payload.update(run_id=orig['run_id'],source_hash=o['source_hash'])
            payload['cutting']['rolls'][0]['yields'][0]['qty_pcs']=str(a)
            d1=v1.save(cur,payload);d2=v2.save(cur,v2.with_pcs(second['payload'],b));conn.commit()
        left=tools.connect();results={};finished_before_commit=False
        try:
            with left.cursor() as cur:
                results['v1']=v1.apply(cur,v1.action(d1))
            def right():
                with tools.connect() as conn,conn.cursor() as cur:
                    try:res=v2.apply(cur,v2.action(d2));conn.commit();return dict(committed=True,result=res)
                    except psycopg.Error as exc:conn.rollback();return dict(committed=False,sqlstate=exc.sqlstate,error=exc.diag.message_primary,detail=exc.diag.message_detail)
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(right)
                deadline=time.monotonic()+3
                while not future.done() and time.monotonic()<deadline:time.sleep(.04)
                finished_before_commit=future.done()
                left.commit();results['v2']=future.result(60)
        finally:left.close()
        with tools.connect() as conn,conn.cursor() as cur:
            rows=cur.execute("select d.target_key,sum((y->>'qty_pcs')::numeric) from cp7_plan_native.intents i join cp7_plan_native.drafts d on d.id=i.draft_id cross join lateral jsonb_array_elements(d.payload->'cutting'->'rolls') r cross join lateral jsonb_array_elements(r->'yields') y where d.id=any(%s::uuid[]) group by d.target_key",([d1['draft_id'],d2['draft_id']],)).fetchall()
            total=sum(D(x[1]) for x in rows)
        witness=dict(capacity=c,planned_quantities=[a,b],committed_total=str(total),results=results,v2_finished_before_v1_commit=finished_before_commit,rows=rows)
        save('AS20-32_v1_v2_capacity',witness)
        check(total<=c,'v1 and v2 must share capacity across uncommitted concurrent plans',**witness)
        return witness

    def revoke_wait():
        with tools.connect() as conn,conn.cursor() as cur:
            owner=h.actor(cur);x=v2.single(cur,today,subject=owner);draft=v2.save(cur,x['payload'],subject=owner);conn.commit()
        q=Queue()
        def send():
            with tools.connect() as conn,conn.cursor() as cur:
                q.put(cur.execute('select pg_backend_pid()').fetchone()[0])
                try:res=v2.apply(cur,v2.action(draft),subject=owner);conn.commit();return dict(committed=True,result=res)
                except psycopg.Error as exc:conn.rollback();return dict(committed=False,sqlstate=exc.sqlstate,error=exc.diag.message_primary)
        with tools.connect() as holder,holder.cursor() as hcur:
            hcur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:PLAN_CAPACITY',0))")
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(send);pid=q.get(timeout=8)
                try:
                    with tools.connect(autocommit=True) as inspector,inspector.cursor() as cur:
                        end=time.monotonic()+8;waiting=False
                        while time.monotonic()<end:
                            waiting=cur.execute("select exists(select 1 from pg_locks where pid=%s and locktype='advisory' and not granted)",(pid,)).fetchone()[0]
                            if waiting:break
                            time.sleep(.04)
                        check(waiting,'Probe observed real lock wait before revocation')
                        cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner,))
                finally:holder.commit()
                got=future.result(60)
        with tools.connect() as conn,conn.cursor() as cur:
            count=cur.execute('select count(*) from cp7_plan_native.intents where draft_id=%s',(draft['draft_id'],)).fetchone()[0]
            check(not got['committed'] and count==0,'Actor revoked during lock wait cannot commit',result=got,intents=count)
        return got

    return [wrap('AS20-32_CROSS_VERSION_CAPACITY',cross_versions),wrap('AS20-03_REVOKE_AFTER_LOCK',revoke_wait)]

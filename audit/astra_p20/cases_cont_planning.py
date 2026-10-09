"""Additional independent numerical planning oracles. Writer helpers only construct/call sources."""
import copy,json,uuid
from datetime import datetime,timedelta
from decimal import Decimal as D
import cp7_planning_schedule_cases as sched
import cp7_planning_netting_cases as net
import cp7_pl5_history_yield_cases as hist
from cases_planning import wilson
from cases_stage import admin,check,wrap,digest_rows

def cases(cur,today):
    def spill():
        sched.opening(cur,today);r=sched.supply.capture(cur,today);p=sched.payload(cur,r)
        check(len(p['config']['positions'])==1,'One independently counted physical queue')
        position=p['config']['positions'][0]
        mins={'SEWING':11,'LAUNDRY':13,'QC':17}
        check(set(s['stage'] for s in position['remaining_steps'])==set(mins),'Fixture traverses three documented production stages')
        for step in position['remaining_steps']:step['remaining_minutes']=str(mins[step['stage']])
        at=datetime.fromisoformat(p['config']['windows'][0]['starts_at'].replace('Z','+00:00'))
        p['config']['unit_minutes']='3'
        p['config']['windows']=[dict(key='as-first',starts_at=sched.stamp(at),ends_at=sched.stamp(at+timedelta(minutes=37)),other_load_minutes='61'),dict(key='as-second',starts_at=sched.stamp(at+timedelta(minutes=37)),ends_at=sched.stamp(at+timedelta(minutes=120)),other_load_minutes='7')]
        sched.save(cur,p);before=sched.b.boundary.snapshot(cur);s=sched.capture(cur,today)
        expected=(37+83-61-7-11-13-17)//3
        check(s['capacity']['status']=='SCENARIO' and D(s['capacity']['capacity_pcs'])==expected==3,'Every owed minute carries forward; integer new-start capacity',observed=s['capacity'])
        check(sched.b.boundary.snapshot(cur)==before,'Scheduling does not create physical production')
        p['expected_revision']='1';p['config']['windows'][0]['other_load_minutes']='121';sched.save(cur,p);bad=sched.capture(cur,today)
        check(bad['capacity']['status']=='UNKNOWN' and bad['capacity']['capacity_pcs'] is None,'Unfinished load beyond calendar never becomes zero/free capacity',observed=bad['capacity'])
        return dict(expected_pcs=3,minutes=dict(windows=[37,83],other=[61,7],existing=[11,13,17],unit=3),normal=s['capacity'],overflow=bad['capacity'])

    def netting():
        f,root,r,p=net.setup(cur,today,True)
        profile=net.baseline.get(cur,[root])['rows'][0]
        net.baseline.save(cur,dict(root_id=root,product_version_id=profile['product_version_id'],expected_revision=profile['revision'],reason='Astra independent13PCS daily need',config=dict(mean_mode='SELECTED_MANUAL',daily_pcs='13',minimum_available_days='20',lead_days='3',review_days='7',buffer_days='0')))
        # A policy update changes the capture binding: use its fresh native source.
        r=sched.supply.capture(cur,today);p=sched.payload(cur,r)
        for x in p['config']['positions']:x.update(yield_numerator='5',yield_denominator='8')
        sched.save(cur,p);n=net.capture(cur,today);x=net.row(n,root)
        check((D(x['raw_gap_pcs']),D(x['directed_on_time_good_pcs']),D(x['base_gap_pcs']))==(D(130),D(5),D(125)),'130need minus5eligible projected pieces; no duplicate stage supply',row=x)
        edges=n['allocation']['allocation']['edges'];check(sum(D(e['input_pcs']) for e in edges)==8 and sum(D(e['projected_good_pcs']) for e in edges)==5,'One eight-piece source counted once globally',edges=edges)
        check(D(n['new_start_capacity']['capacity_pcs'])==37,'Existing WIP and new starts use separate correct budgets',capacity=n['new_start_capacity'])
        saved=json.dumps(n,sort_keys=True)
        at=cur.execute('select clock_timestamp()').fetchone()[0]
        p['expected_revision']='1';p['config']['windows'][0].update(starts_at=sched.stamp(at+timedelta(days=13)),ends_at=sched.stamp(at+timedelta(days=13,hours=2)));p['config']['through_at']=sched.stamp(at+timedelta(days=14))
        sched.save(cur,p);late=net.capture(cur,today);later=net.row(late,root)
        check(D(later['base_gap_pcs'])==130 and D(later['directed_on_time_good_pcs'])==0,'Thirteen-days-late supply cannot cover ten-day need',row=later)
        old=net.read(cur,n['run_id']);check(old['source_state']=='ARCHIVED_STALE' and old['rows']==n['rows'],'Revised schedule never rewrites prior netting result')
        return dict(normal=x,late=later,edges=edges,old_result_unchanged=True)

    def threshold():
        actor=hist.actor(cur);p=hist.product(cur,'AS-cont199');prod=hist.Production(cur,today);hist.save(cur,hist.payload(reason='Approved owner package with independent199/200 boundary fixture'),actor)
        groups=[];cuts=[39,40,40,40,40];goods=[36,37,38,39,40]
        for cut,good in zip(cuts,goods):
            g=prod.group(p,cut,good);groups.append(g);hist.prove(cur,[g['group']])
        before,_=hist.history(cur,p['target'],p['model'],actor)
        check(before['status']=='INSUFFICIENT_SAMPLE' and before['lower_bound'] is None,'Five groups199pieces is below200 threshold',history=before)
        g=prod.group(p,1,1);groups.append(g);hist.prove(cur,[g['group']]);after,_=hist.history(cur,p['target'],p['model'],actor)
        expected=D(str(wilson(sum(goods)+1,200)))
        check(after['status']=='AVAILABLE' and after['groups']=='6' and after['cut_pcs']=='200' and D(after['lower_bound'])==expected,'At200 eligiblepieces use exact independently calculated Wilson bound',expected=str(expected),history=after)
        return dict(cuts=cuts+[1],good=goods+[1],before=before,after=after,independent_wilson=str(expected))

    def exhausted():
        actor=hist.actor(cur);p=hist.product(cur,'AS-cont-reopen');prod=hist.Production(cur,today)
        cuts=[41,42,43,44,45];goods=[38,40,40,41,43];groups=[prod.group(p,c,g) for c,g in zip(cuts,goods)]
        hist.prove(cur,[g['group'] for g in groups]);hist.save(cur,hist.payload(),actor)
        initial,_=hist.history(cur,p['target'],p['model'],actor);check(initial['status']=='AVAILABLE' and D(initial['lower_bound'])==D(str(wilson(sum(goods),sum(cuts)))),'Healthy finished-history control')
        history_before=digest_rows(cur,'cp7_supply_native','exhaustion_proofs');g=groups[0]
        oldproof=next(x['proof_id'] for x in initial['proofs'] if x['group_id']==g['group'])
        hist.b.chain.bs_action(cur,'REVERSE_DISPOSITION',dict(resolution_id=g['resolution'],change_reason='Astra reopened three pieces after proof'),hist.b.chain.version(cur,'bs_cases',g['case']));admin(cur)
        reopened,_=hist.history(cur,p['target'],p['model'],actor)
        level=next(x for x in reopened['levels'] if x['level']=='PRODUCT_SIZE')
        check(reopened['status']=='INSUFFICIENT_SAMPLE' and level['groups']=='4' and D(level['cut_pcs'])==sum(cuts[1:]),'Reopened group excluded despite old exhausted proof',history=reopened)
        check(digest_rows(cur,'cp7_supply_native','exhaustion_proofs')==history_before,'Old proof rows immutable')
        prod.scrap(g,hist.az.chain.production.at(g['day'],14,15));stale,_=hist.history(cur,p['target'],p['model'],actor)
        check(stale['status']=='INSUFFICIENT_SAMPLE','Changed completion cannot reuse an obsolete proof',history=stale)
        hist.prove(cur,[g['group']]);fresh,_=hist.history(cur,p['target'],p['model'],actor)
        newproof=next(x['proof_id'] for x in fresh['proofs'] if x['group_id']==g['group'])
        check(fresh['status']=='AVAILABLE' and fresh['lower_bound']==initial['lower_bound'] and newproof!=oldproof,'A fresh proof restores only the real completed history',history=fresh)
        return dict(initial=initial,reopened=reopened,stale=stale,reproved=fresh)

    return [wrap('AS20C-22-NET',netting),wrap('AS20C-23-SPILL',spill),wrap('AS20C-24-199',threshold),wrap('AS20C-25-REOPEN',exhausted)]

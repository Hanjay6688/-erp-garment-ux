"""Posted-import replay successor; exact dates, quantities, costs and full refusal.

The original ten DAY IMPORT results and all frozen functions are unchanged.
AK/AR checks the finalized batch before the already-posted opening header.
Only that explicit primary refusal differs from the historical AD expectation.
"""
from datetime import date,timedelta
from decimal import Decimal
import psycopg
import cp6_ac_independent_audit as common
import cp6_v2620ad_family_proof as day_oracle
import cp6_v2620ae_family as ae
import cp7_retained_cp6_fixture as fixture
from cp7_ab_bounded_chain import composition as product

IDS=tuple('POSTED_IMPORT_REPLAY:'+kind+':'+zone
    for kind in('FABRIC_ROLL','ACCESSORY')for zone in common.ZONES)
catalog=product.catalog


def replay(cur,opening):
    common.actors.admin(cur)
    statuses=cur.execute('select h.status,b.status from erp.opening_balance_headers h join erp.migration_batches b on b.id=h.migration_batch_id where h.id=%s',(opening,)).fetchone()
    assert statuses==('POSTED','POSTED'),statuses
    cur.execute('set constraints all immediate')
    before_data=catalog._data(cur);before_catalog=catalog._catalog_rows(cur)
    before_legacy=common.actors.boundary(cur)
    cur.execute('savepoint opening_replay_guard');observed=None
    try:
        common.actors.owner(cur)
        cur.execute('select erp.post_opening_balance(%s)',(opening,))
    except psycopg.Error as error:
        observed=dict(sqlstate=error.sqlstate,primary=error.diag.message_primary,raw=str(error))
    finally:
        cur.execute('rollback to savepoint opening_replay_guard')
        common.actors.admin(cur);cur.execute('release savepoint opening_replay_guard')
    assert observed and observed['sqlstate']=='P0001'and observed['primary']=='AK_OPENING_REQUIRES_CURRENT_VALIDATED_BATCH',observed
    actual_data=catalog._data(cur);actual_catalog=catalog._catalog_rows(cur)
    changes={k:dict(before=before_data.get(k),after=actual_data.get(k))
        for k in set(before_data)|set(actual_data)if before_data.get(k)!=actual_data.get(k)}
    assert not changes,('POSTED_IMPORT_REPLAY_CHANGED_ROWS_OR_SEQUENCES',changes)
    assert before_catalog==actual_catalog,'POSTED_IMPORT_REPLAY_CHANGED_FULL22'
    assert common.actors.boundary(cur)==before_legacy,'POSTED_IMPORT_REPLAY_CHANGED_LEGACY_BOUNDARY'
    return dict(status='PASS',observed=observed,posted_header_and_batch=statuses,
        full22_equal=True,all_rows_and_sequences_equal=True,legacy_boundary_equal=True,
        data_before_sha256=catalog.digest(before_data),data_after_sha256=catalog.digest(actual_data),
        catalog_before_sha256=catalog.digest(before_catalog),catalog_after_sha256=catalog.digest(actual_catalog))


def operation(cur,day,kind,zone):
    # Original AC imports/posting, wrong-date controls and ordinary OWNER proof.
    record=common.opening_case(cur,kind,zone,day,'IMPORT')
    assert record['status']=='CONTROL_PASS',record
    material=record['material_id'];e=dict(report=day_oracle.owner_report(cur,day),checkpoints={})
    for at,qty,cost in((day-timedelta(days=1),0,0),(day,10,Decimal('1.25'))):
        cur.execute('select erp.refresh_material_cost_checkpoint(%s,%s)',(material,at))
        row=cur.execute('select checkpoint_date,stock_qty,moving_average_cost from erp.material_cost_checkpoints where material_id=%s',(material,)).fetchone()
        e['checkpoints'][str(at)]=dict(actual=row,expected=[at,qty,cost],matches=row==(at,qty,cost))
    total=common.one(cur,"select sum(l.debit)from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id where j.source_type='OPENING_BALANCE'and j.source_id=%s",(record['opening_id'],))
    assert total==Decimal('12.50'),'OPENING_EXACT_MONEY_CHANGED'
    e['journal_debits']=total;e['replay']=replay(cur,record['opening_id'])
    strict=record['timestamp_matches_day_start']and all(v['qty']==v['expected_qty']for v in record['stock_cutoffs'].values())and all(v['matches']for v in e['checkpoints'].values())
    assert strict,'AE_CROSSFLOW_STOCK_COST_DAY_MISMATCH'
    assert e['report']['data_confidence']['status']=='READY',e['report']
    assert len(e['report']['ad_checks'])==1 and e['report']['ad_checks'][0][2]==0,'AD_NORMAL_DETECTOR_NOT_ZERO'
    e['strict_partition_matches']=strict
    return dict(status='PASS',original_import_result=record,downstream=e,ae_report=ae.assert_ready(cur,day),
        original_dates_quantities_costs_money_ready_oracles_retained=True,legacy_result_relabelled=False)


def cases(cur,today,*,current,evidence):
    day=today-timedelta(days=3)
    common.actors.admin(cur);common.prior.set_open_period(cur,date(2026,8,31))
    fixture.prepare(cur,today,current=current,closed_through=date(2026,8,31),evidence=evidence)
    result=[]
    for kind in('FABRIC_ROLL','ACCESSORY'):
        for zone in common.ZONES:
            name='POSTED_IMPORT_REPLAY:'+kind+':'+zone
            result.append((name,lambda k=kind,z=zone:operation(cur,day,k,z)))
    assert tuple(name for name,_ in result)==IDS
    return result

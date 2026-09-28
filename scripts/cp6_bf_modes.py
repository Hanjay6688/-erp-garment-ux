"""Writer BF incremental qualification. Only listed cases are evidence; CP6 remains HOLD."""
import cp6_bf_probe as bf
import cp6_bb_probe as bb
import cp6_bd_revision_modes as bd_revision
INSTALL_BF=True

def cases(cur,today):
    return [('BF:IMPORT_AMBIGUOUS_FAILS_BEFORE_POST',lambda:bf.import_ambiguity(cur,today)),
        ('BF:IMPORT_EXACT_SIZE_SALES_CUSTODY_COGS_REPLAY',lambda:bf.import_exact(cur,today)),
        ('BF:IMPORT_INSUFFICIENT_STOCK_ATOMIC',lambda:bf.import_insufficient(cur,today)),
        ('BF:IMPORT_REWORK_SOURCE_RECIPE',lambda:bf.import_rework_source(cur,today)),
        ('BF:UNUSED_ROLLBACK_EXACT',lambda:bf.recovery_unused(cur,today)),
        ('BF:USED_ROLLBACK_REFUSED',lambda:bf.recovery_used(cur,today)),
        ('BF:TWO_SKUS_ONE_WAVE_WORK_LAUNDRY_QC',lambda:bf.production_ranges(cur,today)),
        ('BF:SHARED_MASTER_PHYSICAL_ROOTS_REPLAY_GUARD',lambda:bf.foundation(cur,today)),
        ('BF:SINGLETON_BEFORE_ECONOMICS',lambda:bf.optional_economics(cur,today)),
        ('BF:TEMPORAL_31_33_TO_31_34_ATOMIC',lambda:bf.temporal_move(cur,today)),
        ('BF:LEGACY_CONFLICT_ACKNOWLEDGED_AND_FUTURE_PRICES',lambda:bf.conflicts(cur,today))]+[("BF_REG_BD:"+k,lambda f=f:f(cur,bf.b.case_day(today))) for k,_,f in bf.b.PLAN if k.startswith(('T02:','T03:','T04:','T05:','T06:','T07:','T12:','T13:','T20:','DEC01:','T24:','D10:','REV:'))]+[("BF_REG_BB:"+k,lambda f=f:f(cur,today)) for k,_,f in bb.PLAN if 'W02' in k]

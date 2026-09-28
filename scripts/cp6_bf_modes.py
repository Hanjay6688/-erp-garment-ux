"""Writer BF incremental qualification. Only listed cases are evidence; CP6 remains HOLD."""
import cp6_bf_probe as bf
INSTALL_BF=True

def cases(cur,today):
    return [('BF:SHARED_MASTER_PHYSICAL_ROOTS_REPLAY_GUARD',lambda:bf.foundation(cur,today)),
        ('BF:SINGLETON_BEFORE_ECONOMICS',lambda:bf.optional_economics(cur,today)),
        ('BF:TEMPORAL_31_33_TO_31_34_ATOMIC',lambda:bf.temporal_move(cur,today)),
        ('BF:LEGACY_CONFLICT_ACKNOWLEDGED_AND_FUTURE_PRICES',lambda:bf.conflicts(cur,today))]

"""PostgreSQL17 documented table-lock conflicts; no ERP permission implied."""
MODES=('ACCESS SHARE','ROW SHARE','ROW EXCLUSIVE','SHARE UPDATE EXCLUSIVE',
       'SHARE','SHARE ROW EXCLUSIVE','EXCLUSIVE','ACCESS EXCLUSIVE')
# PostgreSQL17 explicit-locking Table13.2, recorded independently of SQL.
CONFLICTS={
 'ACCESS SHARE':{'ACCESS EXCLUSIVE'},
 'ROW SHARE':{'EXCLUSIVE','ACCESS EXCLUSIVE'},
 'ROW EXCLUSIVE':{'SHARE','SHARE ROW EXCLUSIVE','EXCLUSIVE','ACCESS EXCLUSIVE'},
 'SHARE UPDATE EXCLUSIVE':{'SHARE UPDATE EXCLUSIVE','SHARE','SHARE ROW EXCLUSIVE','EXCLUSIVE','ACCESS EXCLUSIVE'},
 'SHARE':{'ROW EXCLUSIVE','SHARE UPDATE EXCLUSIVE','SHARE ROW EXCLUSIVE','EXCLUSIVE','ACCESS EXCLUSIVE'},
 'SHARE ROW EXCLUSIVE':{'ROW EXCLUSIVE','SHARE UPDATE EXCLUSIVE','SHARE','SHARE ROW EXCLUSIVE','EXCLUSIVE','ACCESS EXCLUSIVE'},
 'EXCLUSIVE':set(MODES)-{'ACCESS SHARE'},
 'ACCESS EXCLUSIVE':set(MODES),
}


def conflicts(held,requested):
    if held not in MODES or requested not in MODES:raise ValueError('UNDECLARED_LOCK_MODE')
    return requested in CONFLICTS[held]


def complete(rows):
    expected={(held,requested)for held in MODES for requested in('SHARE','SHARE ROW EXCLUSIVE','EXCLUSIVE')}
    if len(rows)!=24 or {(r['held'],r['requested'])for r in rows}!=expected:raise ValueError('EXACT24_LOCK_PAIRS_REQUIRED')
    for row in rows:
        blocked=conflicts(row['held'],row['requested'])
        if row.get('refused')is not blocked or row.get('sqlstate')!=('55P03'if blocked else None):
            raise ValueError('ACTUAL_LOCK_MATRIX_MISMATCH')
        if row.get('two_actual_backends')is not True or row.get('holder_lock_observed')is not True:
            raise ValueError('ACTUAL_LOCK_HOLDER_REQUIRED')
    return dict(actual_lock_pairs=24,source_contract='PostgreSQL17 Table13.2',
        SHARE_ROW_EXCLUSIVE_excludes_ROW_SHARE=False,EXCLUSIVE_excludes_ROW_SHARE=True,
        EXCLUSIVE_allows_plain_SELECT=True,ERP_relation_set_qualified=False,
        actual_ERP_Native_cases=0,production_go=False,independent_acceptance=False)

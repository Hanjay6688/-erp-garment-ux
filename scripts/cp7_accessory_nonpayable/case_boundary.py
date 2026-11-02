"""Pure complete Native-case boundary and observed sequence accounting.

No sequence is reset. Surviving generated rows plus exact allocations of the
one predeclared failed GOOD explain every allowed Native sequence advance.
The owning complete database restore must still restore ALL sequence values.
"""
OWNED={
    'erp.app_access_audit_id_seq':('erp.app_access_audit','id','i'),
    'erp.audit_logs_id_seq':('erp.audit_logs','id','a'),
    'erp.cost_recalc_queue_id_seq':('erp.cost_recalc_queue','id','a'),
    'erp.production_pattern_audit_id_seq':('erp.production_pattern_audit','id','i'),
}
FG='erp.fg_stock_book_order_seq'
WITNESSES={name:(table,column)for name,(table,column,_)in OWNED.items()}
WITNESSES[FG]=('erp.fg_stock_movements','book_order')
MISSING='NONPAYABLE_NATIVE_MISSING_CATEGORY_EFFECTIVE_DATE_ATOMIC_GOOD_REFUSAL'
MISSING_ERROR=dict(sqlstate='P0001',message='NONPAYABLE_CURRENT_POLICY_EFFECTIVE_DATE_REQUIRED: tetapkan tanggal berlaku ERP-DEC02')
SEQUENCE_DEFINITION=['bigint','1','1','9223372036854775807','1','1',False]

def state(value):
    if(type(value)is not list or len(value)!=2 or type(value[0])is not str or not value[0].isdecimal()
        or str(int(value[0]))!=value[0]or int(value[0])<1 or type(value[1])is not bool):
        raise ValueError('NONPAYABLE_TYPED_POSITIVE_SEQUENCE_STATE_REQUIRED')
    return int(value[0]),value[1]

def allocations(before,after):
    first,called=state(before);last,last_called=state(after)
    if before==after:return []
    minimum=first+(1 if called else 0)
    if not last_called or last<minimum or last-minimum>100000:
        raise ValueError('NONPAYABLE_BOUNDED_MONOTONIC_NATIVE_SEQUENCE_ALLOCATION_REQUIRED')
    return [str(n)for n in range(minimum,last+1)]

def capture_generated(cur,catalog,before):
    """Read exact local Native rows/ALL sequences; never advance an allocator."""
    with catalog._catalog(cur):
        names=cur.execute("select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace "
            "where c.relkind='S'and "+catalog.NAMESPACE+" order by 1,2").fetchall()
        sequences={'sequence:'+'.'.join(name):list(cur.execute(catalog.sql.SQL(
            'select last_value::text,is_called from {}').format(catalog.sql.Identifier(*name))).fetchone())for name in names}
        rows={}
        for name,(table,column)in WITNESSES.items():
            key='sequence:'+name
            if key not in sequences or key not in before['full_data_and_sequences']:
                raise ValueError('NONPAYABLE_ACTUAL_NATIVE_SEQUENCE_WITNESS_MEMBER_REQUIRED:'+name)
            allocated=allocations(before['full_data_and_sequences'][key],sequences[key])
            if not allocated:rows[name]=[];continue
            query=catalog.sql.SQL('select to_jsonb(r)from {} r where {} between %s and %s order by {}').format(
                catalog.sql.Identifier(*table.split('.')),catalog.sql.Identifier(column),catalog.sql.Identifier(column))
            rows[name]=[r[0]for r in cur.execute(query,(int(allocated[0]),int(allocated[-1]))).fetchall()]
    return dict(sequences=sequences,generated_rows=rows)

def expected_refusal_gaps(case_id,result):
    gaps=result.get('actual_sequence_allocations',{})
    if type(gaps)is not dict:raise ValueError('NONPAYABLE_NATIVE_REFUSAL_ALLOCATION_OBJECT_REQUIRED')
    if not gaps:return {}
    if case_id!=MISSING or result.get('actual_error')!=MISSING_ERROR:
        raise ValueError('NONPAYABLE_SEQUENCE_GAPS_REQUIRE_EXACT_DECLARED_NATIVE_GOOD_REFUSAL')
    before=result['before'];after=result['after']
    if before['actual_all22']!=after['actual_all22']or len(before['actual_all22'])!=22:
        raise ValueError('NONPAYABLE_FAILED_POSTING_CHANGED_CATALOG')
    a,b=before['full_data_and_sequences'],after['full_data_and_sequences']
    if set(a)!=set(b)or any(a[k]!=b[k]for k in a if not k.startswith('sequence:')):
        raise ValueError('NONPAYABLE_FAILED_POSTING_CHANGED_ANY_BUSINESS_ROW_OR_SEQUENCE_MEMBER')
    changed={k for k in a if k.startswith('sequence:')and a[k]!=b[k]}
    if set(gaps)!=changed or any(k.removeprefix('sequence:')not in WITNESSES for k in changed):
        raise ValueError('NONPAYABLE_FAILED_POSTING_ONLY_EXACT_OBSERVED_NATIVE_SEQUENCE_GAPS_ALLOWED')
    result={}
    for name,pair in gaps.items():
        if type(pair)is not dict or set(pair)!={'before','after'}or pair['before']!=a[name]or pair['after']!=b[name]:
            raise ValueError('NONPAYABLE_FAILED_POSTING_SEQUENCE_RECEIPT_CHANGED')
        result[name]=allocations(pair['before'],pair['after'])
    return result

def validate(boundary,*,case_id,result):
    before,after,observed=boundary['before'],boundary['after'],boundary['after_operation']
    catalog=before['actual_all22']
    if len(catalog)!=22 or catalog!=after['actual_all22']:
        raise ValueError('NONPAYABLE_NATIVE_CASE_FULL_ALL22_CHANGED')
    a,b=before['full_data_and_sequences'],after['full_data_and_sequences']
    if set(a)!=set(b)or any(a[k]!=b[k]for k in a if not k.startswith('sequence:')):
        raise ValueError('NONPAYABLE_NATIVE_CASE_ALL_ROWS_OR_SEQUENCE_MEMBERS_NOT_RESTORED')
    first={k:v for k,v in a.items()if k.startswith('sequence:')}
    last={k:v for k,v in b.items()if k.startswith('sequence:')}
    if set(first)!=set(observed['sequences'])or last!=observed['sequences']:
        raise ValueError('NONPAYABLE_CASE_SAVEPOINT_MUST_NOT_RESET_OR_DROP_OBSERVED_SEQUENCES')
    gaps=expected_refusal_gaps(case_id,result);accounted={}
    if set(observed['generated_rows'])!=set(WITNESSES):
        raise ValueError('NONPAYABLE_COMPLETE_NATIVE_SEQUENCE_ROW_WITNESSES_REQUIRED')
    for name,(table,column)in WITNESSES.items():
        key='sequence:'+name
        if key not in first or catalog['sequences'].get(name)!=SEQUENCE_DEFINITION:
            raise ValueError('NONPAYABLE_EXACT_UNIT_INCREMENT_UNCACHED_NATIVE_SEQUENCE_REQUIRED:'+name)
        if name in OWNED:
            expected=[OWNED[name][2],table,column]
            if catalog['sequence_ownership'].get(name)!=expected:
                raise ValueError('NONPAYABLE_EXACT_NATIVE_SEQUENCE_OWNERSHIP_REQUIRED:'+name)
        elif catalog['columns']['erp.fg_stock_movements:book_order'][-1]!="nextval('erp.fg_stock_book_order_seq'::regclass)":
            raise ValueError('NONPAYABLE_EXACT_NATIVE_FG_BOOK_ORDER_DEFAULT_REQUIRED')
        allocated=allocations(first[key],last[key]);missing=gaps.get(key,[])
        if not set(missing).issubset(allocated):raise ValueError('NONPAYABLE_REFUSAL_SEQUENCE_GAP_OUTSIDE_ACTUAL_CASE_RANGE')
        rows=observed['generated_rows'][name]
        if type(rows)is not list:raise ValueError('NONPAYABLE_RAW_GENERATED_NATIVE_ROW_ARRAY_REQUIRED')
        identifiers=[str(row[column])for row in rows]
        if len(set(identifiers))!=len(identifiers)or identifiers!=[n for n in allocated if n not in set(missing)]:
            raise ValueError('NONPAYABLE_EVERY_NATIVE_SEQUENCE_ALLOCATION_REQUIRES_ROW_OR_EXACT_FAILED_POSTING_WITNESS:'+name)
        accounted[name]=dict(actual_allocations=len(allocated),actual_surviving_generated_rows=len(rows),
            declared_failed_posting_gaps=missing)
    allowed={'sequence:'+name for name in WITNESSES}
    if any(first[k]!=last[k]for k in first if k not in allowed):
        raise ValueError('NONPAYABLE_NATIVE_CASE_UNEXPECTED_OTHER_SEQUENCE_CHANGE')
    return dict(classification='OBSERVED_NATIVE_ALLOCATIONS_AND_DECLARED_FAILED_GOOD_GAPS_NOT_TRANSACTIONAL_RESTORE',
        all22_catalog_exact=True,all_table_rows_restored=True,all_other_sequences_unchanged=True,
        observed_sequences_unchanged_by_rollback=True,accounted_sequences=accounted,
        case_sequence_reset_performed=False,complete_outer_backup_ALL_sequence_restore_required=True)

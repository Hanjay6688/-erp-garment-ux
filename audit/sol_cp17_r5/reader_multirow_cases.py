"""Independent empty/multirow single-statement controls; no product edits."""
from decimal import Decimal as D
from hashlib import sha256
from pathlib import Path
import json
import uuid
import psycopg
import reader_graph_cases as graph
from reader_input_fixture import build_reader_fixture
from detector_case import detector_rows, counts
import detector_mutable_controls as protected

ID = 'SOL_R5_ALL11_EMPTY_AND_MULTIROW_SINGLE_STATEMENT'


def inputs(cur, today, f, sale_journal, ret_journal):
    missing = uuid.UUID('08d87ac7-eefb-4537-a6c4-d826bf9a5bad')
    all_inputs = graph.expanded_inputs(cur,today,f['po'],f['product'])
    for signature in graph.READERS:
        types = signature.split('(')[1][:-1]
        if types == 'uuid':
            meaningful = [x for x in all_inputs[signature] if x[0] is not None and str(x[0]) != str(missing)]
            assert meaningful, ('SOL_R5_MULTIROW_NO_POSITIVE_INPUT', signature)
            chosen = meaningful[-1]
            if 'compute_po_' in signature: chosen = (f['po'],)
            if 'compute_non_po_' in signature: chosen = (f['product'],)
            all_inputs[signature] = [chosen,(missing,),(None,),chosen]
        elif types == 'uuid,uuid':
            all_inputs[signature] = [(sale_journal,f['po']),(ret_journal,f['po']),(missing,missing),(sale_journal,f['po'])]
        elif types == 'date,date,date':
            all_inputs[signature] = all_inputs[signature][:3] + [all_inputs[signature][0]]
        elif types == '':
            all_inputs[signature] = [(),(),(),()]
        else: raise AssertionError(('SOL_R5_UNLISTED_SIGNATURE',signature))
    return all_inputs


def query(cur, signature, arguments, empty=False):
    graph.claims(cur)
    name, tail = signature.split('(')
    types = tail[:-1].split(',') if tail != ')' else []
    cells=[]; params=[]
    for i,a in enumerate(arguments):
        assert len(types)==len(a)
        cells.append('('+str(i)+''.join(',%s::'+t for t in types)+')')
        params.extend(a)
    columns=['ordinal']+['a'+str(i) for i in range(len(types))]
    stmt = ('with inputs('+','.join(columns)+') as(values '+','.join(cells)+') '
            'select i.ordinal,to_jsonb(x)::text from inputs i cross join lateral '
            +name+'('+','.join('i.a'+str(i) for i in range(len(types)))+') x'
            +(' where false' if empty else '')+' order by i.ordinal,to_jsonb(x)::text')
    cur.execute('savepoint sol_r5_multirow_call')
    try:
        rows=cur.execute(stmt,params).fetchall()
        return dict(kind='ROWS', rows=[list(r) for r in rows])
    except psycopg.Error as e:
        cur.execute('rollback to savepoint sol_r5_multirow_call')
        return dict(kind='ERROR',sqlstate=e.sqlstate,message=str(e).split('\n')[0])
    finally:
        cur.execute('release savepoint sol_r5_multirow_call');graph.bd.api.admin(cur)


def cases(cur, today):
    def multirow():
        o=dict(case_id=ID,oracle_origin='SOL_LITERAL_PO_BOOK_AND_LIFECYCLE_WITH_FULL_CANONICAL_GRAPH_COMPARISON',
               fixture_origin='ACCEPTED_BB_BE_INPUT_BUILDERS_PLUS_NATIVE_PO10_HPP120_SALE2_RETURN1',
               runtime='ISOLATED_LOOPBACK_NATIVE_DATABASE',trigger_or_privilege_changed=False,
               comparison_scope='Four input ordinals per reader, including duplicate/NULL/missing UUID where supported; and WHERE FALSE empty result, all within one SQL statement per reader.')
        try:
            o['writer_input_fixture']=build_reader_fixture(cur,today)
            f=graph.produced(cur,today,'SOL-R5-MULTIROW')
            sale=graph.make_sale(cur,f);ret=graph.make_return(cur,sale)
            sl=graph.lifecycle(cur,'SALE',sale,f['po'],24)
            rl=graph.lifecycle(cur,'SALES_RETURN',ret,f['po'],-12)
            assert graph.book(cur,f['po'])==(D(108),D(12),D(0))
            args=inputs(cur,today,f,sl['journal_id'],rl['journal_id'])
            installed=graph.definitions(cur);old=graph.legacy_graph(installed)
            protected_before=protected.fingerprints(cur)
            def evaluate():
                return {s:dict(multirow=query(cur,s,a),empty=query(cur,s,a,True)) for s,a in args.items()}
            current=evaluate()
            cur.execute('savepoint sol_r5_multirow_full_old_graph')
            try:
                for definition in old.values():graph.bd.api.admin(cur);cur.execute(definition)
                assert graph.definitions(cur)==old
                previous=evaluate()
            finally:
                graph.bd.api.admin(cur);cur.execute('rollback to savepoint sol_r5_multirow_full_old_graph');cur.execute('release savepoint sol_r5_multirow_full_old_graph')
            o.update(installed_answers=current,legacy_graph_answers=previous,
                     input_arguments={s:[list(map(str,a)) for a in x] for s,x in args.items()},
                     installed_definitions_sha256={s:sha256(d.encode()).hexdigest() for s,d in installed.items()},
                     legacy_definitions_sha256={s:sha256(d.encode()).hexdigest() for s,d in old.items()})
            assert current==previous,'SOL_R5_SINGLE_STATEMENT_GRAPH_ANSWERS_CHANGED'
            for s,row in current.items():
                assert row['empty']==dict(kind='ROWS',rows=[]),('SOL_R5_EMPTY_READER_RESULT',s,row['empty'])
                assert row['multirow']['kind']=='ROWS' and {r[0] for r in row['multirow']['rows']}=={0,1,2,3},('SOL_R5_MULTIROW_NOT_EXERCISED',s,row['multirow'])
            po_rows=current['erp.compute_po_hpp_gl_book_v2620e(uuid)']['multirow']['rows']
            expected=[(D(108),D(12),D(0)),(D(0),D(0),D(0)),(D(0),D(0),D(0)),(D(108),D(12),D(0))]
            actual=[tuple(D(str(json.loads(r[1])[k])) for k in ('fg_value','cogs_value','other_out_value')) for r in po_rows]
            assert actual==expected,('SOL_R5_MULTIROW_PO_LITERAL',actual)
            lifecycle=current['erp.sale_lifecycle_po_hpp_amount_v2620d(uuid,uuid)']['multirow']['rows']
            assert [None if json.loads(r[1]) is None else D(str(json.loads(r[1]))) for r in lifecycle]==[D(24),D(-12),None,D(24)],('SOL_R5_MULTIROW_LIFECYCLE_LITERAL',lifecycle)
            assert graph.definitions(cur)==installed and protected.fingerprints(cur)==protected_before
            o['all_nine_detector_outputs']=detector_rows(cur)
            assert len(counts(o['all_nine_detector_outputs']))==167
            o.update(status='PASS',all11_single_statement_outputs_equal=True,all11_empty_outputs_equal=True,
                     own_PO_and_lifecycle_nonzero_exact=True,graph_and_facts_and_guards_restored=True,
                     finite_inputs_only=True,whole_application_equivalence_claim=False)
            return o
        finally:
            p=graph.PRODUCT/'cp6-proof/t3'/(ID+'_OBSERVATIONS.json')
            p.write_text(json.dumps(o,indent=2,default=str)+'\n')
    return [(ID,multirow)]

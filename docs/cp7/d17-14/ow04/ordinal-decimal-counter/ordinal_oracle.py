#!/usr/bin/env python3
"""Independent scalar-rectangle arithmetic oracle, not Native or a DB installer.

EXPECTED.json was frozen first. This uses direct Decimal sums at every rectangle,
not the SQL kernel's cumulative/window implementation. Inverse-pair, registration,
and gross checks below are small contract models, not proof of any ERP authority.
"""
from __future__ import annotations
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
EXPECTED_SHA = '5a47a026f386f9fb66570260731ddff6480d6674db2049cca029effcd0e475db'
ZERO = Decimal('0.00')
checks = 0

def money(v):
    assert isinstance(v, str) and re.fullmatch(r'[+-]?(0|[1-9][0-9]*)(\.[0-9]{1,2})?', v), v
    return Decimal(v)

def exact(v):
    return format(v, '.2f')

def equal(actual, expected, where):
    global checks
    checks += 1
    assert actual == expected, {'where': where, 'actual': actual, 'expected': expected}

def amount_at(events, e, b, kind=None):
    if e is None or b is None:
        return ZERO
    return sum((money(x['amount']) for x in events
                if x['economic_date'] <= e and x['transaction_date'] <= b
                and (kind is None or x['kind'] == kind)), ZERO)

def overflow(events, e, b):
    return max(ZERO, amount_at(events, e, b, 'FUNDING') - amount_at(events, e, b, 'NET'))

def vector(before, after):
    # Evaluate four complete scalar rectangles for each mixed difference.
    es = sorted({x['economic_date'] for x in before + after})
    bs = sorted({x['transaction_date'] for x in before + after})
    result = []
    def delta(e, b):
        return overflow(after, e, b) - overflow(before, e, b)
    for ei, e in enumerate(es):
        for bi, b in enumerate(bs):
            pe = es[ei-1] if ei else None
            pb = bs[bi-1] if bi else None
            value = delta(e, b) - delta(pe, b) - delta(e, pb) + delta(pe, pb)
            if value:
                result.append({'amount': exact(value), 'economic_date': e, 'transaction_date': b})
    return result

def ordinal_vectors(case, families=None, base=None):
    before = list(case['base_events'] if base is None else base)
    answer = {}
    for family in sorted(case['families'] if families is None else families, key=lambda x: x['ordinal']):
        after = before + family['events']
        answer[family['family_id']] = vector(before, after)
        before = after
    return answer

def combine(vectors):
    cells = defaultdict(lambda: ZERO)
    for values in vectors:
        for x in values:
            cells[x['economic_date'], x['transaction_date']] += money(x['amount'])
    return [{'amount':exact(v), 'economic_date':e, 'transaction_date':b}
            for (e,b),v in sorted(cells.items()) if v]

def difference(new, old):
    inverse = [{**x,'amount':exact(-money(x['amount']))} for x in old]
    return combine([new,inverse])

def capacity(components, consumptions, e, b):
    es = sorted({e} | {x['economic_date'] for x in components + consumptions})
    bs = sorted({b} | {x['transaction_date'] for x in components + consumptions})
    def balance(a, c):
        return amount_at(components,a,c) - amount_at(consumptions,a,c)
    return {'balance_at_pair':exact(balance(e,b)),
            'current_balance':exact(balance(es[-1],bs[-1])),
            'future_minimum_balance':exact(min(balance(a,c) for a in es for c in bs if a >= e and c >= b)),
            'source_prefixes_nonnegative':all(balance(a,c) >= ZERO for a in es for c in bs)}

def source_rectangles(case):
    events = case['base_events'] + [x for f in case['families'] for x in f['events']]
    es = sorted({x['economic_date'] for x in events})
    bs = sorted({x['transaction_date'] for x in events})
    return events, es, bs

def authority_model(case, actual):
    """Only the declared model predicates, not factual-source completeness."""
    events, es, bs = source_rectangles(case)
    originals = {x['id']:x for x in events}
    inverse_floor_ok = all(
        x['inverse_of'] in originals
        and money(x['amount']) == -money(originals[x['inverse_of']]['amount'])
        and x['kind'] == originals[x['inverse_of']]['kind']
        and x['economic_date'] >= originals[x['inverse_of']]['economic_date']
        and x['transaction_date'] >= originals[x['inverse_of']]['transaction_date']
        for x in events if 'inverse_of' in x)
    gross = [x for x in case['base_events'] if x['kind'] == 'NET']
    gross_ok = all(amount_at(events,e,b,'FUNDING') <= amount_at(gross,e,b,'NET')
                   for e in es for b in bs)
    capacity_ok = True
    for family_id, values in actual.items():
        consumers = [x for x in case['consumptions'] if x['family_id'] == family_id]
        if consumers:
            capacity_ok &= capacity(values,consumers,es[-1],bs[-1])['source_prefixes_nonnegative']
    return inverse_floor_ok and gross_ok and capacity_ok

def registration_model(case):
    # Deliberately a model: no claim that a database enforces this.
    registered = {}
    def register(identity):
        family_id = identity['family_id']
        if family_id in registered:
            if registered[family_id] != identity:
                raise ValueError('IMMUTABLE_REGISTRATION_MISMATCH')
            return 'SAME_IDENTITY_NO_INSERT'
        if any(x['ordinal'] == identity['ordinal'] for x in registered.values()):
            raise ValueError('IMMUTABLE_REGISTRATION_MISMATCH')
        registered[family_id] = dict(identity)
        return 'INSERT'
    for f in case['families']:
        identity = {'family_id':f['family_id'], 'ordinal':f['ordinal'], 'source_event_id':f['events'][0]['id']}
        equal(register(identity),'INSERT',case['id']+':register:'+f['family_id'])
        equal(register(identity),'SAME_IDENTITY_NO_INSERT',case['id']+':replay:'+f['family_id'])
    equal(len(registered),len(case['families']),case['id']+':registration-count')
    for mutation in case.get('registry_mutations',[]):
        identity = {**registered[mutation['family_id']],**mutation}
        try:
            register(identity)
        except ValueError as exc:
            equal(str(exc),'IMMUTABLE_REGISTRATION_MISMATCH',case['id']+':immutable')
        else:
            raise AssertionError('registration mutation accepted')

def main():
    expected_file = HERE / 'EXPECTED.json'
    equal(hashlib.sha256(expected_file.read_bytes()).hexdigest(), EXPECTED_SHA, 'frozen expected checksum')
    doc = json.loads(expected_file.read_text())
    equal(len(doc['cases']),doc['fixture_count'],'declared count')
    results=[]
    for case in doc['cases']:
        label=case['id']
        expected=case['expected']
        actual=ordinal_vectors(case)
        equal(set(actual),set(expected['families']),label+':family-set')
        for family_id, values in actual.items():
            fexp=expected['families'][family_id]
            equal(values,fexp['components'],label+':vector:'+family_id)
            equal(exact(sum((money(x['amount']) for x in values),ZERO)),fexp['net_current_k'],label+':net:'+family_id)
            equal(bool(values),fexp['has_recognition_effect'],label+':effect:'+family_id)
            equal(fexp['registration_required'],True,label+':empty-registration:'+family_id)
            equal(fexp['explicit_recognition_account_required'],bool(values),label+':explicit-choice:'+family_id)
        aggregate=combine(actual.values())
        equal(aggregate,expected['family_sum'],label+':family-sum')
        events,es,bs=source_rectangles(case)
        full=vector([],events)
        base=vector([],case['base_events'])
        equal(aggregate,difference(full,base),label+':telescoping-subtracts-base')
        equal(exact(overflow(events,es[-1],bs[-1])),expected['source_current_f'],label+':current-F')
        kernel_ok=all(amount_at(events,e,b,k)>=ZERO for e in es for b in bs for k in ('NET','FUNDING'))
        kernel_ok &= all(x['transaction_date'] >= x['economic_date'] for x in events)
        kernel_ok &= all(x['transaction_date'] >= x['economic_date'] for v in actual.values() for x in v)
        equal(kernel_ok,expected['kernel_arithmetic_accepts'],label+':arithmetic-only')
        equal(authority_model(case,actual),expected['source_authority_admissible'],label+':limited-authority-model')
        if expected['source_authority_admissible']:
            equal(base,[],label+':admissible-base-F-zero')
        for key,values in (('source_f_components',full),('base_f_components',base)):
            if key in expected:
                equal(values,expected[key],label+':'+key)
        for check in expected.get('capacities',[]):
            consumers=[x for x in case['consumptions'] if x['family_id']==check['family_id']]
            got=capacity(actual[check['family_id']],consumers,check['economic_date'],check['transaction_date'])
            want={k:check[k] for k in got}
            equal(got,want,label+':capacity:'+check['family_id'])
        if 'pooled_current_balance' in expected:
            consumers=case['consumptions']
            pooled=capacity(aggregate,consumers,es[-1],bs[-1])
            equal(pooled['current_balance'],expected['pooled_current_balance'],label+':pool-is-insufficient')
        if 'aggregate_source_prefixes_nonnegative' in expected:
            equal(all(overflow(events,e,b)>=ZERO for e in es for b in bs),expected['aggregate_source_prefixes_nonnegative'],label+':full-F-nonnegative')
        if 'initial_families' in case:
            if 'initial_base_omit_ids' in case:
                old_base=[x for x in case['base_events'] if x['id'] not in case['initial_base_omit_ids']]
                old_families=case['families']
            else:
                old_base=[x for x in case['base_events'] if 'inverse_of' not in x]
                old_families=[{**f,'events':[x for x in f['events'] if 'inverse_of' not in x]} for f in case['families']]
            old=ordinal_vectors(case,old_families,old_base)
            equal(old,case['initial_families'],label+':literal-initial-vectors')
            adjustments={f:difference(actual[f],old[f]) for f in actual}
            equal(adjustments,expected['adjustments'],label+':literal-append-only-adjustments')
        if expected.get('shuffle_invariant'):
            shuffled=[{**f,'events':list(reversed(f['events']))} for f in reversed(case['families'])]
            equal(ordinal_vectors(case,shuffled,list(reversed(case['base_events']))),actual,label+':retrieval-order')
        if 'forgotten_empty_family_wrong_b_components' in expected:
            forgot=ordinal_vectors(case,[{**case['families'][1],'ordinal':1}])
            equal(forgot['B'],expected['forgotten_empty_family_wrong_b_components'],label+':forget-empty-counter')
        if 'swapped_ordinal_wrong_vectors' in expected:
            swapped=[{**f,'ordinal':3-f['ordinal']} for f in case['families']]
            equal(ordinal_vectors(case,swapped),expected['swapped_ordinal_wrong_vectors'],label+':ordinal-swap-counter')
        registration_model(case)
        results.append({'id':label,'status':'PASS','arithmetic_only':True})
    result={'artifact_kind':'STANDALONE_DECIMAL_RECTANGLE_MODEL_RESULT_NOT_NATIVE',
            'expected_sha256':EXPECTED_SHA,'fixture_count':len(results),'checks':checks,
            'status':'PASS','native_executed':False,'sql_kernel_executed':False,
            'product_installed':False,'source_authority_proven':False,
            'registration_checks_are_model_only':True,'results':results}
    (HERE/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='results'}))

if __name__ == '__main__':
    main()

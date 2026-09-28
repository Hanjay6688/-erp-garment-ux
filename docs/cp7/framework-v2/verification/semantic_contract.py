"""Limited independent preparation checks; NOT a complete ERP runtime validator."""
from decimal import Decimal

def validate_semantics(x):
    errors=[]
    def bad(code): errors.append(code)
    def number(v):
        return Decimal(v['value']) if v.get('state') in ('KNOWN','ASSUMED') else None
    def count(v,path):
        n=number(v)
        if n is not None and v.get('unit')=='PCS' and (n<0 or n!=n.to_integral_value()):bad('COUNT_INVALID:'+path)
    if x['status']=='COMPLETE' and not x['snapshot']['capture_complete']:bad('COMPLETE_WITH_INCOMPLETE_CAPTURE')
    targets={r['target']['key']:r for r in x['recommendations']}
    sources={s['source_key']:s for s in x['sources']}
    if len(targets)!=len(x['recommendations']):bad('DUPLICATE_TARGET')
    if len(sources)!=len(x['sources']):bad('DUPLICATE_SOURCE')
    assumptions={a['id'] for a in x['assumptions']}
    sums={k:[Decimal(0),Decimal(0)] for k in sources}
    for r in x['recommendations']:
        for field in ['actual_fg','target_qty','q_base','q_conditional','suggested_new','rounding_extra','feasible_new','unresolved_qty']:count(r[field],field)
        for aid in r['assumption_ids']:
            if aid not in assumptions:bad('UNRESOLVED_ASSUMPTION')
        if r['production_state']!='ACTIVE' and number(r['suggested_new']) not in (None,0):bad('INACTIVE_START_NEW')
    for edge in x['allocation_edges']:
        sk,tk=edge['source_key'],edge['target_key']
        if sk not in sources or tk not in targets:bad('UNRESOLVED_EDGE');continue
        if edge['size_id']!=sources[sk]['size_id'] or edge['size_id']!=targets[tk]['target']['size_id']:bad('EDGE_SIZE_MISMATCH')
        a,b=number(edge['input_qty']),number(edge['projected_output_qty'])
        count(edge['input_qty'],'edge.input');count(edge['projected_output_qty'],'edge.output')
        if a is None or b is None:bad('ALLOCATION_UNPROVEN');continue
        if a>0 and edge['match'] not in ('CONFIRMED_TARGET','CANDIDATE_MATCH'):bad('INELIGIBLE_MATCH')
        if b>a:bad('OUTPUT_EXCEEDS_INPUT')
        sums[sk][0]+=a;sums[sk][1]+=b
        for aid in edge['assumption_ids']:
            if aid not in assumptions:bad('UNRESOLVED_EDGE_ASSUMPTION')
    for sk,src in sources.items():
        for field in ['physical_remaining','eligible_input','eligible_projected','allocated']:count(src[field],field)
        physical,eligible,projected,allocated=[number(src[k]) for k in ['physical_remaining','eligible_input','eligible_projected','allocated']]
        if None not in (physical,eligible,allocated) and not (0<=allocated<=eligible<=physical):bad('SOURCE_INPUT_CAPACITY')
        if allocated is not None and sums[sk][0]!=allocated:bad('EDGE_INPUT_TOTAL')
        if projected is not None and sums[sk][1]>projected:bad('SOURCE_OUTPUT_CAPACITY')
    for row in x['timeline']:
        if row['target_key'] not in targets:bad('UNRESOLVED_TIMELINE_TARGET')
        b=number(row['balance_end']);backlog=number(row['backlog_qty'])
        if row['mode']=='LOST_SALES' and ((b is not None and b<0) or backlog not in (None,0)):bad('LOST_SALES_CARRIES_BACKLOG')
        if row['mode']=='BACKLOG' and b is not None and backlog is not None and backlog!=max(0,-b):bad('BACKLOG_NOT_RECONCILED')
        if row['timing_basis']=='DATE_POLICY' and not row['timing_policy_id']:bad('TIMING_POLICY_MISSING')
        if row['timing_basis']=='TIMESTAMP_EVIDENCE' and not row['event_refs']:bad('TIMING_EVIDENCE_MISSING')
    for m in x['metrics']:
        if m['scope_kind']=='TARGET' and m['scope_key'] not in targets:bad('UNRESOLVED_METRIC_TARGET')
        if m['period_start']>m['period_end']:bad('METRIC_PERIOD_REVERSED')
    return errors

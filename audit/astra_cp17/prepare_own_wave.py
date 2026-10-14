from pathlib import Path
import ast,hashlib,json,re,yaml

ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'audit/astra_cp17'

def main():
    groups={'money':['business','money_edges','payroll','cont_money','cont_extra'],
        'planning':['edges','planning'],'staged':['stage','cont_state']}
    manifest=dict(round_id='cp17-20261014',candidate_sha='0b7049d9203bac52b47a4c89f3e0d75646067a8f',
        status='PREDECLARED_BEFORE_EXECUTION',oracle_origin='ASTRA_FROZEN_CONTRACT_E800E016',
        original_ref='e800e016',groups={},production_go=False,
        isolation='Candidate P21 FULL; each sequential case rollback, complete boundary/public/function/ACL/session comparison',
        repeat_policy='One attempt; first failure retained; no automatic business-day retry',
        old_case_disclosure={'AS20-39_VALIDATION_NEGATIVE':'Known semantic-corruption detector limitation; original assertion remains, raw COUNTEREXAMPLE retained if observed',
            'AS20C-04-ACTOR':'Original factory emits this ID in two different groups. Two executions, one unique ID; multiplicity retained.'},
        separate_work='New cross-CP cases and Fable-origin leads use their own manifest; old frozen oracles are not claimed as new blind discovery')
    for suite,names in groups.items():
        manifest['groups'][suite]=[]
        for name in names:
            p=HERE/'prior_astra'/('cases_'+name+'.py');b=p.read_bytes();tree=ast.parse(b)
            function=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='cases')
            ids=[x.args[0].value for x in ast.walk(function) if isinstance(x,ast.Call) and isinstance(x.func,ast.Name) and x.func.id=='wrap' and x.args and isinstance(x.args[0],ast.Constant)]
            if name=='cont_extra':ids.insert(0,'AS20C-04-ACTOR')
            manifest['groups'][suite].append(dict(source=str(p.relative_to(ROOT)),git_blob=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),sha256=hashlib.sha256(b).hexdigest(),case_ids=ids,
                role='Ordinary authenticated owner/custom role where case uses public command; explicit admin fixture/observation and private kernel controls retained',
                oracle='Exact frozen case source; independent arithmetic/refusal/immutability checks; no production helper self-comparison substituted'))
    (HERE/'OWN_CASE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    w=yaml.safe_load((ROOT/'.github/workflows/audit-astra-cp17-native.yml').read_text())
    w['name']='AUDIT/Astra/cp17-own-contracts'
    w['run-name']='AUDIT/cp17-20261014/Astra/0b7049d9/own/${{ github.run_attempt }}'
    w['on']['push']['paths']=['.github/workflows/audit-astra-cp17-own.yml','audit/astra_cp17/OWN_START']
    w['concurrency']['group']='astra-cp17-own-${{ github.run_id }}'
    j=w['jobs']['phase'];j['name']='AUDIT/Astra/own-${{ matrix.phase }}';j['strategy']['max-parallel']=3
    j['timeout-minutes']=180
    j['strategy']['matrix']['include']=[dict(phase=p,suite='own-'+p,bucket='') for p in groups]
    for s in j['steps']:
        if s.get('name')=='Prove pinned product and record evidence origins':
            s['run']=s['run'].replace('NATIVE_CASE_MANIFEST.json','OWN_CASE_MANIFEST.json').replace("oracle_origin='WRITER_UNCHANGED'","oracle_origin='ASTRA_FROZEN_CONTRACT_E800E016'")
        elif s.get('name')=='Independently rerun unchanged writer cases on pinned product':
            s['name']='Execute frozen Astra contract oracles on FULL composition'
            s['run']='python "../control/audit/astra_cp17/own_contracts.py" "${{ matrix.phase }}"'
        if 'with' in s and 'name' in s['with']:
            s['with']['name']='cp17-astra-0b7049d9-${{ matrix.suite }}-'+('json' if s['with']['name'].endswith('-json') else 'raw')
    (ROOT/'.github/workflows/audit-astra-cp17-own.yml').write_text(yaml.safe_dump(w,sort_keys=False,width=120))
    # G-01 is a captured-baseline comparison, never a query to hosted Supabase.
    g=yaml.safe_load((ROOT/'.github/workflows/cp6-g01-baseline.yml').read_text())
    g['name']='AUDIT/Astra/cp17-cp1-fingerprint'
    g['run-name']='AUDIT/cp17-20261014/Astra/0b7049d9/cp1/${{ github.run_attempt }}'
    g['on']={'push':{'branches':['audit/astra-cp1-7-0b7049d9-20261014'],'paths':['.github/workflows/audit-astra-cp17-cp1.yml']}}
    g['concurrency']['group']='astra-cp17-cp1-${{ github.run_id }}'
    for s in g['jobs']['baseline']['steps']:
        if s.get('uses','').startswith('actions/checkout') and s.get('with',{}).get('path')=='auditor':
            s['with']['ref']='0b7049d9203bac52b47a4c89f3e0d75646067a8f'
        if s.get('uses','').startswith('actions/upload-artifact'):
            s['with']['name']='cp17-astra-0b7049d9-cp1-fingerprint'
    (ROOT/'.github/workflows/audit-astra-cp17-cp1.yml').write_text(yaml.safe_dump(g,sort_keys=False,width=120))
    print(json.dumps({k:sum(len(m['case_ids']) for m in v) for k,v in manifest['groups'].items()}))

if __name__=='__main__':main()

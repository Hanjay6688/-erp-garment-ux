"""Read-only source/trigger inventory. Never dispatches, repins or admits runtime.

Use an explicit commit and base. GitHub's documented 3,000-file diff limit and
other trigger conditions mean that a local
full-diff path match is not a promise that a push will start a workflow.
"""
from hashlib import sha256
from pathlib import Path,PurePosixPath
import argparse,json,re,subprocess
import yaml

ROOT=Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(['git','-C',str(ROOT),*args])


def match(value,pattern):
    # This repository inventory supports literals, * and ** only; an unknown
    # pattern is reported instead of being silently treated as a non-match.
    if any(c in pattern for c in '?+[]{}\\'):
        raise ValueError('UNSUPPORTED_GLOB: '+pattern)
    parts=[];i=0
    while i<len(pattern):
        if pattern[i:i+3]=='**/':parts.append('(?:.*/)?');i+=3
        elif pattern[i:i+2]=='**':parts.append('.*');i+=2
        elif pattern[i]=='*':parts.append('[^/]*');i+=1
        else:parts.append(re.escape(pattern[i]));i+=1
    return re.fullmatch(''.join(parts),value)is not None


def includes(value,patterns):
    result=False
    for pattern in patterns:
        negative=pattern.startswith('!');raw=pattern[1:]if negative else pattern
        if match(value,raw):result=not negative
    return result


def inventory(base,candidate,branch):
    candidate=git('rev-parse',candidate+'^{commit}').decode().strip()
    base=git('rev-parse',base+'^{commit}').decode().strip()
    paths=git('ls-tree','-r','--name-only',candidate).decode().splitlines()
    changed=git('diff','--name-only',base,candidate).decode().splitlines()
    # One batch reads immutable Git blobs, not the mutable checkout.
    blobs={}
    needed=[p for p in paths if p.startswith('.github/workflows/')and p.endswith(('.yml','.yaml'))
        or p.startswith('scripts/')and p.endswith('/SOURCE.json')]
    for p in needed:blobs[p]=git('show',candidate+':'+p)
    sources={}
    for path in needed:
        if not path.endswith('/SOURCE.json'):continue
        declaration=json.loads(blobs[path]);pins=declaration.get('files')
        if not isinstance(pins,dict):continue
        drift=[]
        for pinned,expected in pins.items():
            if pinned not in paths:actual=None
            else:
                if pinned not in blobs:blobs[pinned]=git('show',candidate+':'+pinned)
                actual=sha256(blobs[pinned]).hexdigest()
            if actual!=expected:drift.append(dict(path=pinned,expected=expected,actual=actual))
        sources[path]=dict(status='PIN_DRIFT'if drift else'PIN_BYTES_MATCH',
            declaration_sha256=sha256(blobs[path]).hexdigest(),pinned_files=len(pins),drift=drift,
            runtime_admitted=False)
    workflows=[]
    for path in needed:
        if not path.startswith('.github/workflows/'):continue
        raw=blobs[path].decode();data=yaml.safe_load(raw);events=data.get('on',data.get(True,{}))
        if isinstance(events,str):events={events:None}
        elif isinstance(events,list):events={e:None for e in events}
        events=events or {};push=events.get('push');eligible='push'in events
        hits=[];error=None
        try:
            if eligible and isinstance(push,dict):
                if 'branches'in push:eligible=includes(branch,push['branches'])
                if 'branches-ignore'in push:eligible=not includes(branch,push['branches-ignore'])
                if eligible:
                    if 'paths'in push:hits=[p for p in changed if includes(p,push['paths'])]
                    elif 'paths-ignore'in push:hits=[p for p in changed if not includes(p,push['paths-ignore'])]
                    else:hits=changed
            elif eligible:hits=changed
        except ValueError as exc:eligible=None;error=str(exc)
        # Only explicit Python entrypoint ancestors are attributed here.
        # Imported/adapted module admission still requires the actual runtime.
        entrypoints=sorted(set(re.findall(r'scripts/[A-Za-z0-9_/-]+\.py',raw)))
        own=[];unresolved=[]
        for script in entrypoints:
            parent=PurePosixPath(script).parent
            while str(parent)not in('.','scripts'):
                declaration=str(parent/'SOURCE.json')
                if declaration in sources:own.append(declaration);break
                parent=parent.parent
            else:unresolved.append(script)
        own=sorted(set(own))
        workflows.append(dict(path=path,name=data.get('name'),push_branch_matches=eligible,
            matches_complete_local_diff=bool(hits),matching_file_count=len(hits),
            matching_file_sample=hits[:4],workflow_dispatch_declared='workflow_dispatch'in events,
            pattern_error=error,explicit_python_entrypoints=entrypoints,
            directly_resolved_source_declarations=own,
            entrypoints_without_ancestor_source_map=unresolved,
            direct_source_status='PIN_DRIFT'if any(sources[x]['drift']for x in own)else
                'RESOLVED_PIN_BYTES_MATCH_ONLY'if own else'NOT_RESOLVED_STATIC',runtime_qualified=False))
    matched=[w for w in workflows if w['push_branch_matches']and w['matches_complete_local_diff']]
    return dict(status='STATIC_INVENTORY_ONLY',base=base,candidate=candidate,branch=branch,
        candidate_tree=git('rev-parse',candidate+'^{tree}').decode().strip(),
        commit_count=int(git('rev-list','--count',base+'..'+candidate)),changed_file_count=len(changed),
        workflow_file_count=len(workflows),complete_local_diff_matches=len(matched),
        matching_workflows=[w['path']for w in matched],
        source_declaration_count=len(sources),source_declarations_with_drift=sum(bool(s['drift'])for s in sources.values()),
        generator_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        github_diff_file_limit=3000,within_github_diff_file_limit=len(changed)<=3000,
        automatic_push_coverage_reliable=False,
        actual_dispatch_predicted=False,branch_updated=False,source_pins_modified=False,
        qualified_case_count=0,independent_acceptance=False,production_go=False,
        documentation='https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#git-diff-comparisons',
        limitations=['Full local diff matching is a planning aid, not the GitHub-dispatched job list.',
            'Matching source bytes is not execution of nested admission or business cases.',
            'Unresolved Python imports and unsupported globs require explicit disposition.',
            'A workflow file is not necessarily a required qualification suite; scope must be mapped to owner requirements.'],
        workflows=workflows,sources=sources)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',required=True);parser.add_argument('--candidate',required=True)
    parser.add_argument('--branch',default='astra/d17-14-integrasi');parser.add_argument('--output',required=True)
    args=parser.parse_args();report=inventory(args.base,args.candidate,args.branch)
    Path(args.output).write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:report[k]for k in('status','candidate','changed_file_count','workflow_file_count',
        'complete_local_diff_matches','source_declaration_count','source_declarations_with_drift',
        'automatic_push_coverage_reliable','qualified_case_count')}))

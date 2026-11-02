"""Root-owned FREE41 immutable source and actual writer-CWD preDB check.

This caller never installs ERP, provisions a database, starts Supabase or runs
a Native case. Four exact historical source Originals are data inputs only.
"""
from pathlib import Path, PurePosixPath
from hashlib import sha256
import argparse, importlib.util, json, os, stat, subprocess, sys, zipfile

HERE=Path(__file__).resolve().parent
AUDITOR=Path(os.environ['GITHUB_WORKSPACE'])/'auditor'
OUT=AUDITOR/'cp6-proof/free41-source-preflight'
HEAD='ad986b9a9d432f2ffac2b961710c3852c6c2ef90'
TREE='80bc5471330b89497991ba1e67615287b01e59c1'
NS='scripts/current-de-free-date-preparation/'
REPO='Hanjay6688/-erp-garment-ux'


def exact(actual,expected,label):
    if type(actual)is not type(expected)or actual!=expected:
        raise ValueError(label)


def pin(raw):
    return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def save(name,value):
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/name).write_text(json.dumps(value,indent=2)+'\n')


def read(name):
    return json.loads((OUT/name).read_bytes())


def git(*args):
    return subprocess.check_output(['/usr/bin/git','-C',str(AUDITOR),*args],text=True).strip()


def identity():
    exact(git('rev-parse','HEAD'),HEAD,'SOURCE_PREFLIGHT_EXACT_CANDIDATE_HEAD')
    exact(git('rev-parse','HEAD^{tree}'),TREE,'SOURCE_PREFLIGHT_EXACT_CANDIDATE_TREE')
    exact(git('rev-parse','--is-shallow-repository'),'false','SOURCE_PREFLIGHT_FULL_HISTORY')
    return dict(head=HEAD,tree=TREE)


def root_source():
    identity()
    sys.path.insert(0,str(HERE))
    import intake_free3 as reader
    with reader.GitBytes(AUDITOR,HEAD,TREE)as g:
        value=reader.source(g)
    exact(value['own_paths'],41,'ROOT_EXACT_OWN41')
    exact(value['source_pins'],40,'ROOT_EXACT_FORTY_SOURCE_PINS')
    exact(value['unchanged_base'],14265,'ROOT_EXACT_ACCEPTED_DE_PARENT_BLOBS')
    exact(value['runtime_fixture_binding_repair']['reversible_routes'],12,'ROOT_EXACT_TWELVE_REPAIR_ROUTES')
    save('ROOT_IMMUTABLE_SOURCE.json',dict(identity=identity(),source=value,actual_Native_cases=0))
    print(json.dumps(dict(status='ROOT_IMMUTABLE_FREE41_SOURCE_PASS_NO_DATABASE',**identity(),
        own_paths=41,source_pins=40,reversible_routes=12,actual_Native_cases=0)),flush=True)


def retained_root_source():
    """Reuse the actual passed immutable gates; the first setup failure stays failed."""
    identity()
    exact(pin((HERE/'intake_free3.py').read_bytes()),
        dict(bytes=28035,sha256='232374b97102bb080433df85d7bd1008c93d8b36feaae1cd4dfd3afb12efe2e8'),
        'EXACT_UNCHANGED_ROOT_READER_FOR_REUSE')
    run=json.loads(subprocess.check_output(['gh','api','repos/'+REPO+'/actions/runs/41387774848']))
    exact(run['head_sha'],'c152bacdcbbd8ef29f3dfcc383fef0f35c6338a7','RETAINED_EXACT_SOURCE_CI_HEAD')
    exact(run['conclusion'],'failure','RETAINED_FIRST_SETUP_FAILURE_NOT_RELABELLED')
    exact(run['run_attempt'],1,'RETAINED_EXACT_SOURCE_CI_ATTEMPT')
    job=json.loads(subprocess.check_output(['gh','api','repos/'+REPO+'/actions/jobs/125092327067']))
    steps={step['name']:step for step in job['steps']}
    exact(steps['Verify Root immutable sources and exact workflow derivation first']['conclusion'],
        'success','RETAINED_ACTUAL_IMMUTABLE_GATES_MUST_HAVE_PASSED')
    exact(steps['Materialize every exact inherited source without database']['conclusion'],
        'failure','RETAINED_ACTUAL_SETUP_FAILURE_PRESERVED')
    raw=subprocess.check_output(['gh','api','repos/'+REPO+'/actions/artifacts/13116231963/zip'])
    exact(pin(raw),dict(bytes=1449,sha256='00af4f9c480c49e30217c7b6bdc75009cf0791bb07c57e12bf52d44ff41a654b'),
        'RETAINED_EXACT_ROOT_SOURCE_CANONICAL_ARCHIVE')
    import io
    with zipfile.ZipFile(io.BytesIO(raw))as archive:
        exact(archive.namelist(),['ROOT_IMMUTABLE_SOURCE.json'],'RETAINED_EXACT_ONE_ROOT_SOURCE_MEMBER')
        exact(archive.testzip(),None,'RETAINED_SOURCE_ARCHIVE_CRC')
        original=archive.read('ROOT_IMMUTABLE_SOURCE.json')
    value=json.loads(original)
    exact(value['identity'],identity(),'RETAINED_EXACT_UNCHANGED_FREE41_IDENTITY')
    exact(value['source']['own_paths'],41,'RETAINED_CLOSED_OWN41')
    exact(value['source']['source_pins'],40,'RETAINED_FORTY_PINS')
    exact(value['actual_Native_cases'],0,'RETAINED_ZERO_BUSINESS_CASES')
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'ROOT_IMMUTABLE_SOURCE.json').write_bytes(original)
    receipt=dict(status='ACTUAL_PASSED_ROOT_SOURCE_AND_WORKFLOW_GATES_REUSED_NOT_RERUN',
        run_id=41387774848,job_id=125092327067,artifact_id=13116231963,archive=pin(raw),
        original=pin(original),first_run_remains_failure=True,actual_new_checks=0,actual_Native_cases=0)
    save('RETAINED_SOURCE_ONLY_CHECKS.json',receipt)
    print(json.dumps(receipt),flush=True)


def source_capacity():
    """Check physical space and inodes for all exact worktrees before copying."""
    identity()
    roots=json.loads((AUDITOR/'scripts/current-finance-combined-composition/FROZEN_SOURCE_ROOTS.json').read_bytes())
    source=json.loads((AUDITOR/'scripts/current-versioned-performance-native-qualification/SOURCE.json').read_bytes())
    replacements={'${{ steps.qualified_heads.outputs.native }}':source['frozen_declaration']['head'],
        '${{ steps.qualified_heads.outputs.B }}':source['B_frozen_head']}
    heads={name:replacements.get(head,head)for name,head in roots.items()}
    heads['qualified-sku090b']='090b85d3fcb738d3e694d4329d306f199a686eb8'
    exact(len(heads),14,'SOURCE_CAPACITY_EXACT_FOURTEEN_WORKTREES')
    filesystem=os.statvfs(AUDITOR)
    needed_bytes=0;needed_files=0
    for name,head in heads.items():
        raw=subprocess.check_output(['/usr/bin/git','-C',str(AUDITOR),'ls-tree','-rlz',head])
        for row in raw.split(b'\0'):
            if not row:continue
            metadata,path=row.split(b'\t',1);parts=metadata.split()
            if parts[1]!=b'blob':raise ValueError('SOURCE_CAPACITY_REGULAR_BLOBS_REQUIRED')
            size=int(parts[3]);needed_files+=1
            needed_bytes+=((size+filesystem.f_frsize-1)//filesystem.f_frsize)*filesystem.f_frsize
    minimum_bytes=needed_bytes+268435456;minimum_inodes=needed_files+10000
    available_bytes=filesystem.f_bavail*filesystem.f_frsize
    receipt=dict(status='EXACT_FOURTEEN_SOURCE_WORKTREE_RESOURCE_PREFLIGHT',
        source_worktrees=14,planned_files=needed_files,planned_physical_file_bytes=needed_bytes,
        minimum_free_bytes=minimum_bytes,minimum_free_inodes=minimum_inodes,
        available_free_bytes=available_bytes,available_free_inodes=filesystem.f_favail,
        actual_Native_cases=0)
    save('SOURCE_RESOURCE_PREFLIGHT.json',receipt)
    print(json.dumps(receipt),flush=True)
    if available_bytes<minimum_bytes or filesystem.f_favail<minimum_inodes:
        raise ValueError('SOURCE_WORKTREE_CAPACITY_INSUFFICIENT_BEFORE_ANY_COPY')


def fetch_originals():
    identity()
    af=json.loads((AUDITOR/'scripts/current-finance-factory-progress-followup-qualification/CONFIG.json').read_bytes())
    config=json.loads((AUDITOR/'scripts/current-finance-combined-composition/PREREQUISITES.json').read_bytes())
    entries=[(af['original_directory_variable'],af['retained_af']),
        (config['original_directory_variable'],config['accepted_consistency']['retained84']),
        (config['retained64_directory_variable'],config['accepted_consistency']['retained64']),
        (config['focused_directory_variable'],config['accepted_consistency']['focused'])]
    exact([entry[1]['artifact_id']for entry in entries],
        [12769642828,12758446701,12763033758,12766592167],'EXACT_FOUR_SOURCE_ORIGINALS_ONLY')
    receipts=[]
    for variable,value in entries:
        folder=Path(os.environ['RUNNER_TEMP'])/'free41-source-originals'/str(value['artifact_id'])
        folder.mkdir(parents=True,exist_ok=False)
        archive=folder/'CANONICAL.zip'
        with archive.open('wb')as stream:
            subprocess.run(['gh','api','repos/'+REPO+'/actions/artifacts/'+str(value['artifact_id'])+'/zip'],
                stdout=stream,check=True)
        exact(pin(archive.read_bytes()),dict(bytes=value['zip_bytes'],sha256=value['zip_sha256']),
            'EXACT_ORIGINAL_CANONICAL_ZIP')
        selected={}
        with zipfile.ZipFile(archive)as source:
            names=source.namelist()
            exact(len(set(names)),len(names),'ORIGINAL_NO_DUPLICATE_MEMBERS')
            for name in names:
                path=PurePosixPath(name)
                if not name or path.is_absolute()or'..'in path.parts or str(path)!=name:
                    raise ValueError('ORIGINAL_SAFE_CANONICAL_MEMBER_REQUIRED')
                mode=source.getinfo(name).external_attr>>16
                if stat.S_ISLNK(mode):raise ValueError('ORIGINAL_SYMLINK_MEMBER_REFUSED')
            exact(source.testzip(),None,'ORIGINAL_ALL_MEMBER_CRC')
            for member,destination,expected in(
                (value['archive_member'],value['name'],dict(bytes=value['bytes'],sha256=value['sha256'])),
                (value['package_member'],value['package_name'],
                    dict(bytes=value['package_bytes'],sha256=value['package_sha256']))):
                raw=source.read(member);exact(pin(raw),expected,'ORIGINAL_EXACT_MEMBER_PIN')
                target=folder/destination
                if target.parent!=folder:raise ValueError('ORIGINAL_OUTPUT_PATH_ESCAPE')
                target.write_bytes(raw);selected[destination]=expected
        with open(os.environ['GITHUB_ENV'],'a')as stream:stream.write(variable+'='+str(folder)+'\n')
        receipts.append(dict(artifact_id=value['artifact_id'],archive=pin(archive.read_bytes()),
            members=len(names),selected_originals=selected,directory_variable=variable))
    with open(os.environ['GITHUB_ENV'],'a')as stream:
        stream.write('PERMANENT_JOIN37_ROOT_INTAKE='+str(AUDITOR/
            'scripts/current-final-s03-sku-s05-preparation/JOIN37_ROOT_ACTUAL_INTAKE.json')+'\n')
    save('FOUR_SOURCE_ORIGINALS.json',dict(status='EXACT_FOUR_SOURCE_ORIGINALS_NO_DATABASE',
        originals=receipts,actual_Native_cases=0))
    print(json.dumps(dict(status='EXACT_FOUR_SOURCE_ORIGINALS_NO_DATABASE',artifacts=len(receipts),
        actual_Native_cases=0)),flush=True)


def final():
    identity()
    root=read('ROOT_IMMUTABLE_SOURCE.json')
    physical=read('PHYSICAL_SOURCE_FENCE.json')
    natural=read('WRITER_CWD_NATURAL_RUNTIME_SOURCE_FENCE.json')
    expected_controls=[
        dict(api='psycopg.connect',result='DENIED_BEFORE_LIBPQ'),
        dict(api='psycopg.Connection.connect',result='DENIED_BEFORE_LIBPQ'),
        dict(api='psycopg.AsyncConnection.connect',result='DENIED_BEFORE_LIBPQ'),
        dict(original_connect_descriptors_restored=True)]
    for name,value in(('physical',physical),('actual_writer_CWD_runtime',natural)):
        guard=value['source_DB_guard']
        exact(guard['attempts'],[],'NO_DB_CONNECTION_ATTEMPTS_'+name)
        exact(guard['network_nonGit_attempts'],[],'NO_NETWORK_OR_NON_GIT_SUBPROCESS_'+name)
        exact(guard['self_controls'],expected_controls,'ORIGINAL_THREE_API_FENCE_AND_RESTORATION_'+name)
        exact(guard['public_source_sha256'],
            '1439d70810383db377c48e043df7fb6d487a1b2f1a995e8993a2c08590f9f797',
            'EXACT_ORIGINAL_PUBLIC_DATABASE_FENCE_'+name)
    exact(physical['source']['own_paths'],41,'PHYSICAL_CLOSED_OWN41')
    exact(physical['source']['unchanged_parent_blobs_and_modes'],14265,'PHYSICAL_UNCHANGED_DE_PARENT')
    exact(natural['entire_natural_product_source_graph_evaluated'],True,'ENTIRE_NATURAL_GRAPH')
    exact(natural['actual_Native_cases'],0,'SOURCE_CHECK_ZERO_BUSINESS_CASES')
    bindings=natural['actual_fixture_and_runner_binding']
    expected=dict(status='EXACT_OWNING_FREE3_FIXTURE_AND_STRICT_RUNNER_BOUND_BEFORE_SQL',
        actual_working_directory=str(AUDITOR.parent/'writer'),callable_API_bindings=7,
        private_fixture_and_runner_aliases=True,canonical_module_cache_replaced=False,
        fixture_or_runner_original_files_changed=False,
        actual_original_output=str(AUDITOR/'cp6-proof/aw'),actual_SQL_executed=0,actual_Native_cases=0)
    for key,value in expected.items():exact(bindings[key],value,'ACTUAL_WRITER_CWD_BINDING_'+key)
    exact(set(bindings['modules']),{'cp7_current_de_free_date/composition.py','cp6_bc_probe.py',
        'cp6_auditor_runner.py'},'EXACT_THREE_BOUND_SOURCE_MODULES')
    for name,value in bindings['modules'].items():
        actual=AUDITOR/'scripts'/name
        exact(value,dict(**pin(actual.read_bytes()),path=str(actual)),'EXACT_OWNING_SOURCE_MODULE_'+name)
    value=dict(status='EXACT_FREE41_WRITER_CWD_FIXTURE_API_SOURCE_FENCE_PASS_NO_DATABASE',
        **identity(),root_source=root['source'],actual_fixture_binding=bindings,
        physical_and_natural_database_fences_pass=True,
        whole_natural_product_graph_evaluated=True,actual_DB_connection_attempts=0,
        actual_Native_cases=0,actual_SQL_executed=0,source_only=True,
        production_go=False,independent_acceptance=False)
    save('FREE41_SOURCE_PREFLIGHT_FINAL.json',value)
    print('FREE41_SOURCE_PREFLIGHT_FINAL_JSON='+json.dumps(value,separators=(',',':')),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=('root-source','retained-root-source','source-capacity','fetch-originals','final'),required=True)
    args=parser.parse_args()
    {'root-source':root_source,'retained-root-source':retained_root_source,'source-capacity':source_capacity,
        'fetch-originals':fetch_originals,'final':final}[args.mode]()

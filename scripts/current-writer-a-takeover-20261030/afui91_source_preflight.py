"""Root-owned immutable Afui91 source and real writer-CWD domain preflight.

No database provisioning, ERP installation or business case is executed.
The existing public database fence wraps the real complete natural loader.
"""
from pathlib import Path, PurePosixPath
from hashlib import sha256
import argparse, importlib.util, json, os, stat, subprocess, sys, zipfile

HERE=Path(__file__).resolve().parent
AUDITOR=Path(os.environ['GITHUB_WORKSPACE'])/'auditor'
OUT=AUDITOR/'cp6-proof/afui91-source-preflight'
HEAD='f4f16c6920d94c2b9ef22fa33c62144595a672ed'
TREE='c2957cd8ee7c7ac00450a5cd636e39ff0e27675c'
NS='scripts/cp7_accessory_nonpayable/'
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
        folder=Path(os.environ['RUNNER_TEMP'])/'afui91-source-originals'/str(value['artifact_id'])
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

def root_source():
    identity()
    sys.path.insert(0,str(HERE))
    import intake_afui15 as reader
    with reader.GitBytes(AUDITOR,HEAD,TREE)as g:
        value=reader.source(g)
    exact(value['own_paths'],91,'AFUI_ROOT_EXACT_OWN91')
    exact(value['source_pins'],58,'AFUI_ROOT_EXACT58_PINS')
    exact(value['unchanged_parent_paths'],14306,'AFUI_ROOT_UNCHANGED_PARENT14306')
    exact(value['parent_qualification_pending'],False,'AFUI_ACTUAL_PARENT_REQUIRED')
    save('ROOT_IMMUTABLE_SOURCE.json',dict(identity=identity(),source=value,actual_Native_cases=0))
    print(json.dumps(dict(status='ROOT_IMMUTABLE_AFUI91_SOURCE_PASS_NO_DATABASE',**identity(),
        own_paths=91,source_pins=58,actual_Native_cases=0)),flush=True)


def final():
    identity()
    root=read('ROOT_IMMUTABLE_SOURCE.json')
    physical=read('PHYSICAL_STATIC_SOURCE.json')
    natural=read('WRITER_CWD_NATURAL_DOMAIN_SOURCE_FENCE.json')
    exact(physical['status'],'NONPAYABLE_STATIC_WHOLE_QUALIFIER_PREPARED_NOT_EXECUTED','AFUI_COMPLETE_STATIC_QUALIFIER')
    for key,value in dict(own_paths=91,own_source_pins=58,unchanged_parent_paths=14306,
        accepted_parent_bound=True,actual_SQL_executed=0,actual_Native_cases=0).items():
        exact(physical['source'][key],value,'AFUI_PHYSICAL_SOURCE_'+key)
    exact(natural['status'],'ACTUAL_FREE3_PARENT_AND_COMPLETE_NONPAYABLE_SOURCE_GRAPH_ADMITTED','AFUI_ACTUAL_COMPLETE_GRAPH')
    guard=natural['source_DB_guard']
    exact(guard['attempts'],[],'AFUI_NO_DB_CONNECTION_ATTEMPTS')
    exact(guard['network_nonGit_attempts'],[],'AFUI_NO_NETWORK_OR_NON_GIT_SUBPROCESS')
    expected_controls=[dict(api='psycopg.connect',result='DENIED_BEFORE_LIBPQ'),
        dict(api='psycopg.Connection.connect',result='DENIED_BEFORE_LIBPQ'),
        dict(api='psycopg.AsyncConnection.connect',result='DENIED_BEFORE_LIBPQ'),
        dict(original_connect_descriptors_restored=True)]
    exact(guard['self_controls'],expected_controls,'AFUI_ORIGINAL_THREE_ENTRYPOINT_FENCE_AND_RESTORATION')
    exact(guard['public_source_sha256'],'1439d70810383db377c48e043df7fb6d487a1b2f1a995e8993a2c08590f9f797','AFUI_EXACT_PUBLIC_FENCE')
    exact(natural['entire_natural_product_source_graph_evaluated'],True,'AFUI_ENTIRE_NATURAL_GRAPH')
    exact(natural['actual_Native_cases'],0,'AFUI_SOURCE_ZERO_BUSINESS_CASES')
    binding=natural['actual_domain_and_caller_binding']
    expected=dict(status='EXACT_AFUI_NATURAL_DOMAIN_AND_CALLER_APIS_BOUND_BEFORE_SQL',
        actual_working_directory=str(AUDITOR.parent/'writer'),constructor_signature_bound=True,
        constructor_chain_global_unchanged=True,strict_runner_API_bound=True,
        canonical_module_cache_replaced=False,original_domain_sources_changed=False,
        actual_SQL_executed=0,actual_Native_cases=0,
        actual_original_output=str(AUDITOR/'cp6-proof/aw'))
    for key,value in expected.items():exact(binding[key],value,'AFUI_REAL_DOMAIN_BINDING_'+key)
    modules={'cp6_bc_probe.py','cp6_bd_probe.py','cp7_invoice_cases.py','cp7_qc_source_cases.py',
        'cp6_auditor_runner.py','cp7_accessory_standard_report/cases.py'}
    exact(set(binding['actual_modules']),modules,'AFUI_EXACT_SIX_REAL_DOMAIN_MODULES')
    frozen={'cp6_bc_probe.py','cp6_bd_probe.py','cp6_auditor_runner.py','cp7_invoice_cases.py'}
    for name,value in binding['actual_modules'].items():
        declared_root=AUDITOR.parent/'qualified-sku090b'if name in frozen else AUDITOR
        actual=declared_root/'scripts'/name
        exact(actual.read_bytes(),(AUDITOR/'scripts'/name).read_bytes(),'AFUI_IDENTICAL_DECLARED_NATURAL_COPY_'+name)
        exact(value,dict(path=str(actual),**pin(actual.read_bytes())),'AFUI_EXACT_REAL_MODULE_'+name)
    if not binding['actual_call_bindings']:raise ValueError('AFUI_NO_REAL_CALLBACKS_BOUND')
    parent=json.loads((AUDITOR/NS/'FREE3_PARENT_ROOT_ACTUAL_INTAKE.json').read_bytes())
    exact(parent['head'],'91a7b46ed13c4ad6094114871a4a39fa6765d140','AFUI_ACTUAL_FREE45_PARENT')
    exact(physical['source']['base_head'],parent['head'],'AFUI_SAME_ACTUAL_BOUND_PARENT')
    exact(physical['source']['base_tree'],parent['tree'],'AFUI_SAME_ACTUAL_BOUND_PARENT_TREE')
    value=dict(status='EXACT_AFUI91_WRITER_CWD_DOMAIN_API_SOURCE_FENCE_PASS_NO_DATABASE',
        **identity(),root_source=root['source'],actual_domain_binding=binding,
        actual_parent_root_receipt=pin((AUDITOR/NS/'FREE3_PARENT_ROOT_ACTUAL_INTAKE.json').read_bytes()),
        physical_static_and_natural_database_fence_pass=True,
        entire_natural_product_source_graph_evaluated=True,
        actual_DB_connection_attempts=0,actual_Native_cases=0,actual_SQL_executed=0,
        source_only=True,production_go=False,independent_acceptance=False)
    save('AFUI91_SOURCE_PREFLIGHT_FINAL.json',value)
    print('AFUI91_SOURCE_PREFLIGHT_FINAL_JSON='+json.dumps(value,separators=(',',':')),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=('root-source','source-capacity','fetch-originals','final'),required=True)
    args=parser.parse_args()
    {'root-source':root_source,'source-capacity':source_capacity,
        'fetch-originals':fetch_originals,'final':final}[args.mode]()

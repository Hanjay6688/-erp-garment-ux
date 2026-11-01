"""Check the existing published global19 profile against saved actual metadata.

Read-only compatibility evidence only. The profile's runtime entry stays
unarmed; no Native function, permission test, or writer lock is executed.
"""
from hashlib import sha1
from pathlib import Path
import argparse,json

from intake_common import GitBytes,exact,pin,require
from intake_sku27 import strict
import preflight_saved_native_metadata as saved

HEAD='a6ded9cd4ce23a6d59cd32e42ca9bb33d793f8cc'
TREE='55da7c6ab29d9bfda68962be27da0db7ad931662'
NS='scripts/current-global-nonpo-actual19-profile-qualification/'
FILES={
 'scripts/cp7_global_nonpo_native_graph_adapter/AUTHORITY.json':dict(bytes=71436,sha256='193194184cdbfde1753677ad486d7010ada8ed9e6198f9a19e57c4b8587e3d78'),
 NS+'CAPTURE.json':dict(bytes=53674,sha256='7bae0b9efd389ca70a66b322fafca54e05538ad7d5b42b4f5d68f46d962f48e0'),
 NS+'ACTUAL_NATIVE_AUTHORITY.sql':dict(bytes=29335,sha256='6be8df6f6fab74d702e2b96e1fdec40ae62e6f8ed176377c6f3a3f93049db4b4'),
 NS+'SOURCE.json':dict(bytes=6960,sha256='d8b4bc5079007ce4cda0695177d9863193ddf55f4ac48704ce1011b50062dcec'),
}


def profile(root,directory):
    values={};files=[];directory=Path(directory)
    with GitBytes(root,HEAD,TREE)as git:
        for name,expected in FILES.items():
            path=directory/Path(name).name
            require(not any(p.is_symlink()for p in(path,*path.parents)),'GLOBAL19_REGULAR_SOURCE_BYTES_REQUIRED')
            raw=path.read_bytes();exact(pin(raw),expected,'GLOBAL19_PINNED_ORIGINAL:'+name)
            entry=git.git('ls-tree','-z',HEAD,'--',name)
            metadata,actual_name=entry[:-1].split(b'\t',1);mode,kind,blob=metadata.decode().split()
            exact(actual_name.decode(),name,'GLOBAL19_EXACT_GIT_PATH');exact((mode,kind),('100644','blob'),'GLOBAL19_GIT_MODE')
            exact(sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),blob,'GLOBAL19_EXACT_IMMUTABLE_GIT_BLOB')
            values[Path(name).name]=raw;files.append(dict(path=name,**expected,git_blob=blob))
    manifest=strict(values['SOURCE.json']);capture=strict(values['CAPTURE.json']);authority=strict(values['AUTHORITY.json'])
    for row in files:
        if row['path']in manifest['files']:
            exact(manifest['files'][row['path']],dict(bytes=row['bytes'],sha256=row['sha256'],mode='100644'),
                'GLOBAL19_ORIGINAL_MANIFEST_PIN:'+row['path'])
    saved.typed(None,manifest['runtime_entry'],'unarmed_runtime');saved.typed(0,manifest['actual_Native_credit'],'profile_credit')
    saved.typed(False,capture['current_final_composite_accepted'],'prior_final_composite_not_accepted')
    exact(capture['functions'],authority['actual_source_profile']['functions'],'GLOBAL19_CAPTURE_AND_AUTHORITY_IDENTICAL')
    exact(len(capture['functions']),19,'GLOBAL19_ALL_ORIGINAL_NINETEEN')
    exact(set(capture['functions']),set(authority['known_functions']),'GLOBAL19_KNOWN_FUNCTION_SET')
    order=authority['actual_source_profile']['function_row_fields']
    exact(order[4:8],['security_definer','leakproof','strict','returns_set'],'GLOBAL19_ORIGINAL_FULL19_BOOLEAN_ORDER')
    return capture['functions'],dict(head=HEAD,tree=TREE,exact_profile_inputs=files,
        existing_published_source_reused=True,previous_profile_models_not_rerun=True,runtime_entry=None)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--profile-directory',type=Path,required=True);parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--api-metadata',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();expected,source=profile(args.source,args.profile_directory)
    snapshot,identity=saved.archive_snapshot(args.archive,strict(args.api_metadata.read_bytes()))
    result=saved.validate(expected,snapshot,expected_count=19)
    result.update(profile_source=source,actual_metadata_original=identity,actual_snapshot=snapshot['snapshot'],
        explicit_corruption_controls=saved.negative_controls(expected,snapshot,expected_count=19),
        boolean_schema_controls=saved.boolean_schema_controls(expected,snapshot,expected_count=19),
        all_global_guards_and_command_hooks_remain_unqualified=True)
    with args.output.open('x')as output:output.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:result[key]for key in('status','functions','attributes_per_function','actual_ERP_cases')}))


if __name__=='__main__':main()

"""Root intake of original midnight Native1; no database or business execution."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
import argparse
import importlib.util
import json
import os
import subprocess
import sys
import zipfile

HEAD='e7875cde9709c7375335bade4e1010be9459163e'
NS='scripts/current-attendance-midnight-source475-qualification/'
ZIP_PIN=(8001776,'5bb0d0fd4247f12e1c28a7716c04a880c4ddb2639d519b7a5132061d6719c194')


def require(ok,message):
    if not ok:raise ValueError(message)


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


class GitBytes:
    def __init__(self,root):
        self.process=subprocess.Popen(['/usr/bin/git','-C',str(root),'cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            env=dict(os.environ,GIT_NO_LAZY_FETCH='1'))
    def read(self,name,ref=HEAD):
        self.process.stdin.write((ref+':'+name+'\n').encode());self.process.stdin.flush()
        header=self.process.stdout.readline().decode().strip().split()
        require(len(header)==3 and header[1]=='blob','ROOT_EXACT_GIT_BLOB_REQUIRED:'+name)
        raw=self.process.stdout.read(int(header[2]));require(self.process.stdout.read(1)==b'\n','ROOT_GIT_STREAM_BOUNDARY')
        return raw
    def close(self,failed=False):
        try:self.process.stdin.close()
        except BrokenPipeError:
            if not failed:raise
        status=self.process.wait()
        if not failed:require(status==0,'ROOT_GIT_READER_FAILED')


def read_zip(path,expected,members):
    raw=Path(path).read_bytes();require((len(raw),sha256(raw).hexdigest())==expected,'ROOT_EXACT_ORIGINAL_ZIP_REQUIRED')
    z=zipfile.ZipFile(path);require(len(z.infolist())==members and z.testzip()is None,'ROOT_ORIGINAL_ZIP_MEMBER_OR_CRC_FAILURE')
    require(len(set(z.namelist()))==members,'ROOT_DUPLICATE_ORIGINAL_ZIP_MEMBER')
    return z


def intake(root,archive,parent_archive):
    root=Path(root).resolve();g=GitBytes(root)
    try:
        actual_head=subprocess.check_output(['/usr/bin/git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
        require(actual_head==HEAD,'ROOT_EXACT_QUALIFIED_SOURCE_HEAD_REQUIRED')
        cfg=json.loads(g.read(NS+'CONFIG.json'));source_raw=g.read(NS+'SOURCE.json');source=json.loads(source_raw)
        require(len(source['files'])==566 and source['actual_current_source_members']==475,'ROOT_COMPLETE_SOURCE566_CURRENT475_REQUIRED')
        tree={}
        for row in subprocess.check_output(['/usr/bin/git','-C',str(root),'ls-tree','-rz',HEAD]).split(b'\0'):
            if row:
                meta,name=row.split(b'\t',1);tree[name.decode()]=meta.decode().split()
        history=json.loads(g.read('scripts/current-workflow-history-isolation/ARCHIVE.json'))
        historical={x['path']:x for x in history['files']};proof_inputs=[]
        for name,expected in source['files'].items():
            if name in tree:raw=g.read(name)
            else:
                require(name in historical,'ROOT_UNDECLARED_NON_GIT_SOURCE:'+name)
                entry=historical[name];raw=g.read(entry['archive'])
                require(raw==g.read(name,history['base_head']),'ROOT_HISTORICAL_SOURCE_NOT_EXACT')
                proof_inputs.append(name)
            require(pin(raw)==expected,'ROOT_CURRENT_SOURCE_PIN_MISMATCH:'+name)
        # Every imported qualifier module is the physical exact public blob.
        for name,(mode,kind,blob)in tree.items():
            if name.startswith(NS)and name.endswith('.py'):
                p=root/name;require(p.is_file()and not p.is_symlink()and p.read_bytes()==g.read(name),'ROOT_IMPORTED_SOURCE_CHANGED:'+name)
        parent_source=cfg['backend_binding']['source_manifest']
        require((root/parent_source['path']).read_bytes()==g.read(parent_source['path']),'ROOT_CURRENT475_PHYSICAL_SOURCE_CHANGED')
        for name,digest in cfg['prepared_backend_runtime7'].items():
            require(sha256(g.read(name)).hexdigest()==digest,'ROOT_ACTUAL_RUNTIME7_SOURCE_CHANGED')
    finally:g.close(failed=sys.exc_info()[0]is not None)
    parent_pin=cfg['accepted_parent14_archive']
    z=read_zip(archive,ZIP_PIN,119)
    pz=read_zip(parent_archive,(parent_pin['bytes'],parent_pin['sha256']),parent_pin['expected_members'])
    try:
        parent_docs={};parent_pins={}
        for key,name in parent_pin['selected_root_names'].items():
            raw=pz.read(name);require(pin(raw)==cfg['accepted_parent14']['originals'][key]['raw'],'ROOT_PARENT_RAW_ORIGINAL_PIN_CHANGED')
            parent_docs[key]=json.loads(raw);parent_pins[name]=pin(raw)
        names=['CP7_ATTENDANCE_MIDNIGHT_NATIVE1.json','CP7_ATTENDANCE_MIDNIGHT_NATIVE1_CASES.json',
               'T3_PACKAGE_INSTALL.json','T3_PACKAGE_FILES_INSTALL.json','T3_BACKUP_RESTORE_DRILL.json']
        originals={name:z.read(name)for name in names};docs={name:json.loads(raw)for name,raw in originals.items()}
        sys.path.insert(0,str(root/NS))
        spec=importlib.util.spec_from_file_location('root_exact_midnight_result_gate',root/NS/'result_gate.py')
        gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
        result=gate.checked(*(docs[name]for name in names),parent_docs,cfg,HEAD)
        require(result==json.loads(z.read('MIDNIGHT_NATIVE1_FINAL_GATE.json')),'ROOT_ORIGINAL_FINAL_GATE_RECOMPUTATION_DIFFERS')
        outer=docs[names[0]];group=docs[names[1]];component=outer['committed'][gate.CASE];fact=group['cases'][gate.ID]
        require(component['midnight_native1']==group,'ROOT_RAW_GROUP_NOT_EXACT_EMBEDDED_GROUP')
        raw_pin=component['midnight_strict_original']
        require(raw_pin['bytes']==len(originals[names[1]])and raw_pin['sha256']==sha256(originals[names[1]]).hexdigest(),'ROOT_STRICT_GROUP_RAW_BYTES_DIFFER')
        rows=fact['physical_rows'];require(len(rows)==2,'ROOT_EXACT_TWO_NATIVE_OUTPUT_ROWS_REQUIRED')
        require(rows[1]['event_epoch_us']-rows[0]['event_epoch_us']==1,'ROOT_EXACT_ONE_MICROSECOND_REQUIRED')
        epoch=datetime(1970,1,1,tzinfo=timezone.utc)
        for row,day in zip(rows,fact['output_dates']):
            instant=epoch+timedelta(microseconds=row['event_epoch_us'])
            require(row['qty']==5 and row['work_status']=='POSTED'and row['event_epoch_us']==row['work_epoch_us'],'ROOT_NATIVE_PHYSICAL_FACT_CHANGED')
            require(instant.astimezone(ZoneInfo('Asia/Jakarta')).date().isoformat()==row['wib_day']==day,'ROOT_WIB_BOUNDARY_RECOMPUTATION_FAILED')
            require(instant.date().isoformat()==row['utc_day'],'ROOT_UTC_BOUNDARY_RECOMPUTATION_FAILED')
            require(row['contractor_id']==row['work_contractor_id']==fact['contractor_id'],'ROOT_NATIVE_CONTRACTOR_MISMATCH')
        require(rows[0]['utc_day']==rows[1]['utc_day']and rows[0]['wib_day']!=rows[1]['wib_day'],'ROOT_SAME_UTC_DISTINCT_WIB_DAYS_REQUIRED')
        for label,index in [('BEFORE',0),('AFTER',1)]:
            preview=fact['previews'][label]
            require(preview['destination_ids']==[rows[index]['event_id']]and preview['source_cents']==100003 and preview['denominator']==5,
                    'ROOT_EXACT_SINGLE_DAY_NATIVE_PREVIEW_FAILED')
        both=fact['previews']['BOTH']
        require(set(both['destination_ids'])=={r['event_id']for r in rows}and both['denominator']==10 and both['source_cents']==100003,
                'ROOT_EXACT_TWO_DAY_NATIVE_PREVIEW_FAILED')
        before=component['Native_financial_truth_before'];after=component['Native_financial_truth_after']
        require(before==after and all(type(x)is int and x==0 for x in before.values()),'ROOT_NATIVE_FINANCIAL_TRUTH_NOT_ALL_ZERO_AND_UNCHANGED')
        require(docs[names[2]]['run_identity']['run_id']=='41007933625','ROOT_NEW_PACKAGE_RUN_CHANGED')
        return dict(result,status='ROOT_VERIFIED_NARROW_MIDNIGHT_NATIVE1_RAW_SOURCE_RESTORE_ALL5',result_gate_status=result['status'],head=HEAD,
            tree=subprocess.check_output(['/usr/bin/git','-C',str(root),'rev-parse','HEAD^{tree}'],text=True).strip(),
            run_id='41007933625',artifact_id=12958410980,archive=pin(Path(archive).read_bytes()),
            originals={name:pin(raw)for name,raw in originals.items()},retained_parent_originals=parent_pins,
            own_source=pin(source_raw),verified_source_pins=566,current_parent_source_members=475,
            exact_historical_proof_inputs=proof_inputs,physical_WIB_boundary_recomputed=True,
            actual_case_id=gate.ID,Native_financial_truth_count=len(before),strict_original_equals_embedded=True,
            full_used_inverse_no_effect=True,full_outer_restore_all22_all_rows_ALL_sequences_roles_Auth_CP6=True,
            all_five_package_gates=True,retained_parent14_reexecuted=False)
    finally:z.close();pz.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in('source-root','archive','parent-archive','output'):p.add_argument('--'+name,required=True)
    args=p.parse_args();value=intake(args.source_root,args.archive,args.parent_archive)
    target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))

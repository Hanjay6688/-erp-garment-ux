"""Natural read-only source/runtime proof under the five real Original inputs.

This never admits install/verify/rollback. Run in a fresh local process. Database
entry calls and network sockets are refused by tracing/auditing, not by replacing
any product function, module ROOT or sources() result.
"""
from pathlib import Path
from hashlib import sha256
import argparse
import importlib.util
import json
import os
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
KEYS=('D17_18_RETAINED_COMBINED_AF_DIRECTORY','CP7_VENDOR_BACKEND11_ORIGINALS',
 'D17_18_ACCEPTED_CONSISTENCY_DIRECTORY','D17_18_RETAINED_FOCUSED64_DIRECTORY',
 'D17_18_ACCEPTED_CONSISTENCY_FOCUSED_DIRECTORY')


def observe_runtime_return(frame,value,forwarding,returns):
    # Inspect only the explicitly named product frames. A foreign tuple
    # subclass can have a computed __len__; observing it must not execute it.
    path=Path(frame.f_code.co_filename)
    if path.is_relative_to(ROOT):
        key=(str(path.relative_to(ROOT)),frame.f_code.co_name)
        if key in forwarding:returns.append((key,value))


def main(environment):
    values=json.loads(Path(environment).read_bytes())
    if set(values)!=set(KEYS)or not all(isinstance(v,str)and Path(v).is_dir()for v in values.values()):
        raise ValueError('FINAL_PARENT_EXACT_FIVE_REAL_ORIGINAL_DIRECTORIES_REQUIRED')
    spec=importlib.util.spec_from_file_location('closed_parent_source_guard',HERE/'guard.py')
    guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
    before=guard.check()
    reads=set();blocked=[];runtime_returns=[]
    forwarding={
      ('scripts/cp7_final_composition/composition.py','source_runtime'),
      ('scripts/cp7_attendance_period_choice/composition.py','runtime'),
      ('scripts/cp7_final_global_bridge/composition.py','runtime'),
      ('scripts/cp7_sku_pair_conversion/composition.py','runtime'),
      ('scripts/cp7_credit_correction_de/e_composition.py','runtime'),
      ('scripts/cp7_credit_correction_de/composition.py','runtime'),
      ('scripts/cp7_vendor_receivable/composition.py','runtime'),
      ('scripts/current-factory-initial-stage/composition.py','runtime'),
    }
    def audit(event,args):
        if event in('socket.connect','socket.getaddrinfo','socket.gethostbyname'):
            blocked.append(event);raise RuntimeError('FINAL_PARENT_SOURCE_INSPECTION_NETWORK_REFUSED')
        if event=='subprocess.Popen':
            argv=args[1]
            if not isinstance(argv,(tuple,list))or Path(str(argv[0])).name!='git'or any(x in argv for x in('fetch','pull','push','clone')):
                raise RuntimeError('FINAL_PARENT_SOURCE_INSPECTION_SUBPROCESS_REFUSED')
        if event=='open'and args and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.fsdecode(args[0]))
            if not p.is_absolute():p=Path.cwd()/p
            if p.is_relative_to(ROOT):reads.add(str(p.relative_to(ROOT)))
    def no_database(frame,event,arg):
        if event=='call'and str(frame.f_globals.get('__name__','')).startswith(('psycopg','psycopg2','asyncpg'))and frame.f_code.co_name in('connect','connect_async','execute','executemany','cursor'):
            blocked.append('DB_ENTRY_CALL');raise RuntimeError('FINAL_PARENT_SOURCE_INSPECTION_DB_ENTRY_REFUSED')
        if event=='return':observe_runtime_return(frame,arg,forwarding,runtime_returns)
    sys.addaudithook(audit)
    oldpath=list(sys.path);oldenv={k:os.environ.get(k)for k in KEYS};oldprofile=sys.getprofile()
    try:
        os.environ.update(values);sys.path.insert(0,str(ROOT/'scripts'));sys.setprofile(no_database)
        from cp7_final_composition import composition as final
        natural=final.sources();runtime_returns.clear();runtime=final.source_runtime()
        if({key for key,value in runtime_returns}!=forwarding
           or not all(value is runtime for key,value in runtime_returns)):
            raise ValueError('FINAL_PARENT_ONE_CALL_RUNTIME_FORWARDING_NOT_EXACT')
        forwarding_proof=[dict(path=key[0],function=key[1],same_tuple_object_from_one_call=value is runtime,
            same_five_module_objects=all(a is b for a,b in zip(value,runtime)))for key,value in runtime_returns]
        report=natural['predecessor'];attendance=report['parent'];global_source=attendance['predecessor']
        sku_source=global_source['predecessor'];e=sku_source['predecessor'];d=e['predecessor'];vendor=d['predecessor']
        order=[natural['contract'],report['stage']['contract'],attendance['contract'],global_source['contract'],
               sku_source['contract'],e['contract'],d['contract'],vendor['contract']]
        expected=['cp7.final-composition-parent-adapters-prepared.v1','cp7.accessory-standard-report.stage.v1',
          'cp7.attendance-period-choice.v1','cp7.final-global-bridge-closed-source.v1',
          'cp7.sku-pair-conversion.v1','cp7.note-credit-carry.v1','cp7.credit-correction-de.v1','cp7.vendor-receivable.v1']
        if order!=expected:raise ValueError('FINAL_PARENT_ACTUAL_NATURAL_SOURCE_ORDER_CHANGED')
        module_facts=[]
        for module in runtime:
            path=Path(module.__file__).resolve()
            if not path.is_relative_to(ROOT):raise ValueError('FINAL_PARENT_RUNTIME_MODULE_OUTSIDE_ACTUAL_ROOT')
            raw=path.read_bytes();module_facts.append(dict(name=module.__name__,path=str(path.relative_to(ROOT)),bytes=len(raw),sha256=sha256(raw).hexdigest()))
    finally:
        sys.setprofile(oldprofile);sys.path[:]=oldpath
        for key,value in oldenv.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value
    declaration=json.loads((HERE/'SOURCE.json').read_bytes());pins={r['path']:r for r in declaration['files']}
    oldtree=guard.tree(guard.BASE);io_facts=[]
    for name in sorted(reads):
        p=ROOT/name
        if not p.is_file():continue
        raw=p.read_bytes()
        if name in pins:guard.read_exact(ROOT,name,pins[name]);kind='CURRENT_DECLARED_LEAF'
        elif name in oldtree:
            if raw!=guard.git('show',guard.BASE+':'+name):raise ValueError('FINAL_PARENT_INHERITED_ACTUAL_READ_CHANGED:'+name)
            kind='EXACT_INHERITED_BASE_GIT_LEAF'
        elif name==str((HERE/'SOURCE.json').relative_to(ROOT)):kind='CURRENT_SOURCE_MANIFEST_SELF'
        elif name in declaration['exact_historical_untracked_inputs']:
            guard.read_exact(ROOT,name,declaration['exact_historical_untracked_inputs'][name]);kind='EXACT_HISTORICAL_NONTRIGGER_INPUT'
        else:raise ValueError('FINAL_PARENT_ACTUAL_UNDECLARED_SOURCE_READ:'+name)
        io_facts.append(dict(path=name,kind=kind,bytes=len(raw),sha256=sha256(raw).hexdigest()))
    after=guard.check()
    if before!=after or blocked:raise ValueError('FINAL_PARENT_SOURCE_OR_ENTRY_BOUNDARY_CHANGED')
    payload=json.dumps(natural,sort_keys=True,separators=(',',':')).encode()
    return dict(classification='ACTUAL_NATURAL_SOURCE_AND_FIVE_MODULE_FORWARDING_ONLY_NOT_DB_OR_ADMISSION',
        status='NATURAL_SOURCE_INSPECTION_COMPLETE',natural_sources=natural,natural_source_order=order,
        natural_graph_sha256=sha256(payload).hexdigest(),runtime_five_original_modules=module_facts,
        runtime_forwarding_one_call=forwarding_proof,separate_runtime_call_identity_assumed=False,
        actual_five_Original_environment_keys=list(KEYS),actual_project_read_files=io_facts,
        product_ROOT_or_method_or_sources_projection=False,DB_network_attempts=blocked,
        runtime_entry=None,accepted_component_bindings=dict.fromkeys(('D1','E','SKU','S03','S05')),
        global_parent_binding=None,actual_Native_Auth_HTTP_browser_races=0,production_go=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--environment',required=True)
    args=parser.parse_args();print(json.dumps(main(args.environment)))

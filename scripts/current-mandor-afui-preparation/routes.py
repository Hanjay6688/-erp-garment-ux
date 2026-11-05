"""Exact source-only adoption of the current Afui parent and report writer."""
from hashlib import sha256

BASE = 'c296fd06167ddd177e1192c1008992e2a1e3d628'
BASE_TREE = 'fdd36962a7de81482ccca02e6ff96597cfc20081'
AFUI = '2b8da485be0dd35e7be2c77e8278537d717e5733'
AFUI_TREE = '29bfe0e40e6f9bce46a259cbb4210149da6a16c6'
PRIOR_AFUI = '76b3f1e1bcce49cc405e55f92a733dcd0f360cad'
NS = 'scripts/current-mandor-shop-native-qualification/'
PINS = {
    'admission.py': (1447, '609db7cade09a03be8aa4777adac6e11fdf3fc5aec672e625ed96705381e3b6c'),
    'qualification.py': (7161, '3f4bf0cfccbf650240729e01909dcb39b3e88371e59ee14a3bffc5f05934de0b'),
    'component.py': (7956, '31b7626e2488fd4371daa2bf21254583b86299673b91130eb0736778126f5044'),
    'access_runtime.py': (8404, '4718579f49a6ad7cc5b4ac0e229d474a61dfe8e13f0e544b6ecf3ac49699a487'),
    'browser_observer.py': (3746, '0458e0314827d2ff2b7c1ac13157e7fc34730f7231289b515c29c280594250f4'),
    'browser_gate.py': (10213, '8b213c1f7bc4232b9edc43471c16e4b0aeb5404c9784359024d9242074a019ad'),
    'preflight.py': (10968, 'ea789817b7ec0c48ca3fb702c5f1a8045853438f87302ea38d81f89595a5069d'),
}


def replacements(name):
    if name == 'preflight.py':
        return (
            ("admission['PARENT_HEAD']=='" + PRIOR_AFUI + "'", "admission['PARENT_HEAD']=='" + AFUI + "'"),
            ("admission['PARENT_TREE']=='b3182ae21e3981e91d6d3730ec4ffb33dce1afb4'",
             "admission['PARENT_TREE']=='" + AFUI_TREE + "'"),
            ("admission['PARENT_RUN']==41596005356", "admission['PARENT_RUN'] is None"),
            ("admission['PARENT_JOB']==125783405360", "admission['PARENT_JOB'] is None"),
        )
    if name == 'admission.py':
        return (
            ("PARENT_HEAD='" + PRIOR_AFUI + "'", "PARENT_HEAD='" + AFUI + "'"),
            ("PARENT_TREE='b3182ae21e3981e91d6d3730ec4ffb33dce1afb4'", "PARENT_TREE='" + AFUI_TREE + "'"),
            ('PARENT_RUN=41596005356', 'PARENT_RUN=None'),
            ('PARENT_JOB=125783405360', 'PARENT_JOB=None'),
        )
    if name == 'qualification.py':
        return (
            ('    text,engine_proof=package_engine.derive(original.read_bytes())\n',
             '    text,engine_proof=package_engine.derive(original.read_bytes())\n'
             "    report_io=load('mandor_current_complete_report_writer',ROOT/'scripts/current-mandor-afui-preparation/report_io.py')\n"
             "    text,output_proof=report_io.derive_packet(text,'mandor17')\n"
             '    engine_proof=dict(retained_complete_engine=engine_proof,complete_report_output=output_proof)\n'),
            ("    engine=ModuleType('writer_a_mandor_exact_whole_package_engine');engine.__file__=str(original)\n",
             "    engine=ModuleType('writer_a_mandor_exact_whole_package_engine');engine.__file__=str(original)\n"
             '    engine.__dict__[report_io.HELPER]=report_io.write_complete\n'),
            ("ROOT/'scripts/current-unified-candidate/check_source.py'", "ROOT/'scripts/current-mandor-afui-preparation/check_source.py'"),
        )
    if name == 'component.py':
        return (
            ('    observed=native.strict_group(NATIVE_LABEL,factory,verify)\n',
             "    report_io=load('mandor_current_owning_group_report_writer',ROOT/'scripts/current-mandor-afui-preparation/report_io.py')\n"
             "    output=load('mandor_current_complete_case_output',ROOT/'scripts/current-mandor-afui-preparation/output_binding.py')\n"
             "    with report_io.group_scope(native.r1),output.case_scope(native,'native'):\n"
             '        observed=native.strict_group(NATIVE_LABEL,factory,verify)\n'),
            ("        raw=path.read_bytes()\n"
             "        if target.exists():require(target.read_bytes()==raw,'MANDOR_NATIVE_FIRST_STRICT_ORIGINAL_CHANGED')\n"
             "        else:\n"
             "            with target.open('xb')as output:output.write(raw)\n"
             "        originals.append(source_record(target))\n",
             "        originals.append(output.copy_exact(path,target))\n"),
        )
    if name == 'browser_observer.py':
        return ((
            "        data=path.read_bytes();require(sha256(data).hexdigest()==os.environ[env],'MANDOR_BROWSER_EXACT_OWNING_ORIGINAL')\n"
            "        docs.append(json.loads(data))\n",
            "        if name=='MANDOR_BROWSER_STATE.json':\n"
            "            state_path=ROOT/'scripts/current-mandor-afui-preparation/state_io.py'\n"
            "            import importlib.util\n"
            "            spec=importlib.util.spec_from_file_location('mandor_complete_browser_state',state_path)\n"
            "            state_io=importlib.util.module_from_spec(spec);spec.loader.exec_module(state_io)\n"
            "            docs.append(state_io.read(path,os.environ[env],os.environ['MANDOR_BROWSER_STATE_CACHE_SHA256']))\n"
            "        else:\n"
            "            data=path.read_bytes();require(sha256(data).hexdigest()==os.environ[env],'MANDOR_BROWSER_EXACT_OWNING_ORIGINAL')\n"
            "            docs.append(json.loads(data))\n"),)
    if name == 'browser_gate.py':
        return ((
            "    state=pinned(p,directory,part['browser_state_original'],'MANDOR_BROWSER_STATE.json')\n",
            "    state_io=access_runtime.load('mandor_final_complete_state_io',access_runtime.ROOT/'scripts/current-mandor-afui-preparation/state_io.py')\n"
            "    state=state_io.verified(p,directory,part['browser_state_original'],part['browser_state_cache_original'])\n"),)
    if name == 'access_runtime.py':
        save = (
            "    path=ROOT/'cp6-proof/t3'/name\n"
            "    raw=(json.dumps(value,sort_keys=True,default=str)+'\\n').encode()\n"
            "    require(not path.exists(),'MANDOR_FIRST_SESSION_ORIGINAL_OVERWRITE_REFUSED')\n"
            "    path.parent.mkdir(parents=True,exist_ok=True)\n"
            "    with path.open('xb')as stream:stream.write(raw)\n"
            "    return dict(name=path.name,bytes=len(raw),sha256=sha256(raw).hexdigest())\n",
            "    output=load('mandor_current_complete_access_output',ROOT/'scripts/current-mandor-afui-preparation/output_binding.py')\n"
            "    return output.save_access(value,name)\n")
        scoped = []
        for key in ('access_copy_authority', 'http_copy_authority', 'browser_copy_authority'):
            before = "    with copy_scope(modes,product,state)as copies:\n        report['" + key + "']=copies\n"
            after = ("    output=load('mandor_current_complete_access_output',ROOT/'scripts/current-mandor-afui-preparation/output_binding.py')\n"
                     "    with output.case_scope(modes,'copies',retention=access_cases),copy_scope(modes,product,state)as copies:\n"
                     "        report['" + key + "']=copies\n")
            scoped.append((before, after))
        state_routes = (
            ("        MANDOR_BROWSER_STATE_SHA256=report['browser_state_original']['sha256'],\n",
             "        MANDOR_BROWSER_STATE_SHA256=report['browser_state_original']['sha256'],\n"
             "        MANDOR_BROWSER_STATE_CACHE_SHA256=report['browser_state_cache_original']['sha256'],\n"),
            ("    report['browser_state_original']=save(state,'MANDOR_BROWSER_STATE.json')\n"
             "    output=load('mandor_current_complete_access_output',ROOT/'scripts/current-mandor-afui-preparation/output_binding.py')\n",
             "    report['browser_state_original']=save(state,'MANDOR_BROWSER_STATE.json')\n"
             "    output=load('mandor_current_complete_access_output',ROOT/'scripts/current-mandor-afui-preparation/output_binding.py')\n"
             "    report['browser_state_cache_original']=output.load_state_io().reference(report['browser_state_original'])\n"),
        )
        return (save, *scoped, *state_routes)
    raise ValueError('MANDOR_CURRENT_ONLY_REVIEWED_CALLER_SOURCES')


def derive(raw, name):
    if name not in PINS or (len(raw), sha256(raw).hexdigest()) != PINS[name]:
        raise ValueError('MANDOR_CURRENT_EXACT_PREPARED_CALLER_SOURCE_REQUIRED:' + name)
    source = raw.decode()
    routes = replacements(name)
    for before, after in routes:
        if source.count(before) != 1 or after in source:
            raise ValueError('MANDOR_CURRENT_ONE_EXACT_CALLER_ROUTE_REQUIRED:' + name)
        source = source.replace(before, after, 1)
    restored = source
    for before, after in reversed(routes):
        if restored.count(after) != 1:
            raise ValueError('MANDOR_CURRENT_ONE_EXACT_INVERSE_ROUTE_REQUIRED:' + name)
        restored = restored.replace(after, before, 1)
    if restored.encode() != raw:
        raise ValueError('MANDOR_CURRENT_COMPLETE_PREPARED_CALLER_NOT_RECOVERED:' + name)
    compile(source, 'current-mandor-afui-caller::' + name, 'exec', dont_inherit=True)
    return source.encode(), dict(original_bytes=len(raw), original_sha256=PINS[name][1],
                                 derived_sha256=sha256(source.encode()).hexdigest(), exact_routes=len(routes),
                                 whole_original_caller_recovered=True, actual_ERP_cases=0, production_go=False)

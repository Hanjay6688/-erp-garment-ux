"""Exact source-only adoption of the current Afui parent and report writer."""
from hashlib import sha256

BASE = 'c296fd06167ddd177e1192c1008992e2a1e3d628'
BASE_TREE = 'fdd36962a7de81482ccca02e6ff96597cfc20081'
AFUI = '92a376091a1d1ea9901648e614f3e5212677a81f'
AFUI_TREE = 'ef194e421402ae1e45625e2d57f58c848ef9e08f'
PRIOR_AFUI = '76b3f1e1bcce49cc405e55f92a733dcd0f360cad'
NS = 'scripts/current-mandor-shop-native-qualification/'
PINS = {
    'admission.py': (1447, '609db7cade09a03be8aa4777adac6e11fdf3fc5aec672e625ed96705381e3b6c'),
    'qualification.py': (7161, '3f4bf0cfccbf650240729e01909dcb39b3e88371e59ee14a3bffc5f05934de0b'),
    'component.py': (7956, '31b7626e2488fd4371daa2bf21254583b86299673b91130eb0736778126f5044'),
}


def replacements(name):
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
             '    with report_io.group_scope(native.r1):\n'
             '        observed=native.strict_group(NATIVE_LABEL,factory,verify)\n'),
        )
    raise ValueError('MANDOR_CURRENT_ONLY_THREE_REVIEWED_CALLER_SOURCES')


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

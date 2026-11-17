"""Bind the retained disposable Auth lifecycle to the dated writer identity."""

from pathlib import Path
import sys
from types import SimpleNamespace
from uuid import uuid4

from . import installed_types_only, installed_types_writer, owning, package_routes


AUTH = 'agents/global-auth-recovery'
COMPONENT = 'nov13-recovery/global-owning-lanes/compose_runtime_routes.py'
PATCH = 'nov13-recovery/global-moving-average-compatibility/GLOBAL_CURRENT_COMPOSED_WRITER_CLOSED.patch'
SOURCES = {
    AUTH + '/auth_adapter.py': 'd32fe4ea3a40e576660d3e99604bc0b0300339096bc1dd0de72d861429b6deab',
    AUTH + '/local_rest.py': '6fe996b74c73a95bcfca9e6e6b62d22b3f5012f817268cbf8c64eda28897fbf0',
    AUTH + '/source_binding.py': '26b3a71fcbd5943a12f7e13ceab02892a57552a3055aaa83313eda8926cdbfca',
    AUTH + '/cleanup_routes.py': '5317e69e31aeae26659f93830a4021641f7a7486a9fbc39592bf1320a35de70d',
    COMPONENT: '08f9fe447c3762df01541b8f5968bdd55168950d3760f79462177ee3cd13f7bb',
    PATCH: '43383d3ea504963d55a8d1c66f3ba30cc7748e559eab0d70ae5b1e5e0dfb8ecc',
}
MODES = 'scripts/cp6_auditor_modes.py'
MODES_SHA = 'd927c7491c72fe1eecfd1b4b8b4faf7e1710d6943fda601ede6a599fbc99209f'
ORIGINALS_SHA = 'f7c732004e1f5f0f2fe7ac7e08a6f049e6d41f0074fca7336c66736aaf522170'
PLAN_SHA = '9abc105fc1dc760deea622d2b97dbfac5f23c2f10ba96574d20d941a6e7f12e5'
DUMP_CLEANUP = "        drill.docker('rm','-f',PRE_DUMP,check=False)\n"
GUARDED_DUMP_CLEANUP = (
    '        if pre_dumped and _global_auth_full_restore_proven(report):\n'
    '    ' + DUMP_CLEANUP +
    '        elif pre_dumped:\n'
    "            report['baseline_dump_cleanup']='SKIPPED_UNVERIFIED_FULL_RESTORE'\n"
)


def preserve_restore_dump(source):
    owning.require(source.count(DUMP_CLEANUP) == 1 and GUARDED_DUMP_CLEANUP not in source,
                   'GLOBAL_AUTH_EXACT_DUMP_CLEANUP_ROUTE_REQUIRED')
    guarded = source.replace(DUMP_CLEANUP, GUARDED_DUMP_CLEANUP, 1)
    owning.require(guarded.replace(GUARDED_DUMP_CLEANUP, DUMP_CLEANUP, 1) == source,
                   'GLOBAL_AUTH_DUMP_CLEANUP_SOURCE_NOT_RECOVERED')
    compile(guarded, '<Global owning writer with guarded dump cleanup>', 'exec', dont_inherit=True)
    return guarded


def bind(audit, candidate, plan_path, originals, *, require_reviewed):
    """Read the unchanged wire, cleanup and ordinary allowlist under the source fence."""
    files = {name: owning.exact(audit / name, expected) for name, expected in SOURCES.items()}
    owning.exact(plan_path, PLAN_SHA)
    plan = owning.load('global_dated_auth_case_plan', plan_path)
    from audit.codex.auth_identity import bind as bind_auditor_identity
    plan = bind_auditor_identity(plan, owning)
    path = candidate / MODES
    modes_raw = owning.exact(path, MODES_SHA)
    originals_raw = owning.exact(Path(originals.__file__).absolute(), ORIGINALS_SHA)
    with owning.import_paths(audit / AUTH, candidate / 'scripts'):
        retained = owning.load('global_dated_auth_source', audit / AUTH / 'source_binding.py')
        # These are bare imports in the donor. Refuse a cached module from another checkout.
        for name in ('auth_adapter', 'local_rest', 'cleanup_routes'):
            module = sys.modules[name]
            rel = f'{AUTH}/{name}.py'
            owning.require(Path(module.__file__).absolute() == audit / rel,
                           'GLOBAL_AUTH_EXACT_RETAINED_MODULE_REQUIRED:' + name)
        modes = owning.load('global_dated_exact_auditor_modes', path)
    retained.exact_module_functions(modes, modes_raw, ('_call',), ('_status_env',), ('Http', '_auth'),
                                    ('Http', '_rpc'), ('HttpUser', '__init__'), ('HttpUser', 'rpc'))
    retained.exact_module_functions(originals, originals_raw, ('save_sorted',))
    compose = owning.load('global_dated_auth_writer_composer', audit / COMPONENT)
    cleanup = retained.cleanup_routes
    restore_fields = sys.modules['auth_adapter'].FULL_RESTORE
    foundation = SimpleNamespace(
        COMMIT=owning.AFTER_COMMIT,
        AFTER_COMMIT=owning.AFTER_COMMIT + '            _global_lifecycle.foundation.after_commit(cur,report)\n',
        derive=lambda source, routes: (owning.foundation_writer(source), None),
    )

    def compose_writer(source):
        reviewed = compose.compose_writer(source, foundation, cleanup, files[PATCH])
        return preserve_restore_dump(reviewed)

    def attempt(identity, output):
        require_reviewed()
        settings = plan.attempt_kwargs(identity)
        transport = retained.OwnedRest(modes, candidate, settings['attempt'], uuid4().hex[:12])
        output = Path(output)

        def save(name, value):
            output.mkdir(parents=True, exist_ok=True)
            return originals.save_sorted(output / name, value, 'GLOBAL_AUTH_CONFLICTING_OWNING_ORIGINAL')

        # The source fence temporarily replaces psycopg.connect. Resolve it when the writer runs.
        bound = retained.Attempt(connect=lambda *args, **kwargs: modes.psycopg.connect(*args, **kwargs),
                                 transport=transport, retain=save, **settings)
        plan.check_attempt(bound, identity)
        return bound

    def writer(engine, lifecycle, runner, report_io, original, revised, identity, auth):
        require_reviewed()
        plan.check_attempt(auth, identity)
        text = compose_writer(revised)

        def bind_original(engine, lifecycle, runner, report_io, source, changed, candidate):
            return package_routes.bind(engine, lifecycle, runner, report_io, source, changed, candidate,
                                       source_identity=identity)

        def full_restore_proven(report):
            return (not report.get('restore_error') and all(report.get(key) is True for key in restore_fields)
                    and (report.get('baseline_restore') or {}).get('only_pg_cron_errors') is True)

        result = compose.private_auth_package(SimpleNamespace(bind=bind_original), engine, lifecycle, runner,
                                              report_io, original, text, candidate, auth, cleanup.error_code)
        result.run_inner.__globals__['_global_auth_full_restore_proven'] = full_restore_proven
        observer = installed_types_only if installed_types_only.enabled() else installed_types_writer
        observer.bind(result, text, report_io, lifecycle, candidate)
        return result

    return SimpleNamespace(attempt=attempt, writer=writer, plan=plan, compose_writer=compose_writer,
                           sources={name: owning.pin(raw) for name, raw in files.items()})


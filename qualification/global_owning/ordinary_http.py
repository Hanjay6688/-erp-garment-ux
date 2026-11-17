"""Bind the exact prepared ordinary Auth sources inside the owning source fence."""

from importlib import import_module
from pathlib import Path

from . import owning


SOURCES = {
    'auth_case_plan': '9abc105fc1dc760deea622d2b97dbfac5f23c2f10ba96574d20d941a6e7f12e5',
    'payload_routes': '5d74fd1c0c28ca3b672353799c5f82a7afa854ca3b1f49d7e52a64f637643297',
    'credit_http': '79bfe70f0bb46a063f1bc4284f278bb1f2115e20c1d779d144050c3bbeb032d5',
    'auth_credit_fixtures': 'f193146fe195d8bf26fd16354a7084a2128a5da54da68540a0e51ec930613d41',
    's05_report_http': 'ed5ba3d8fe73f697b4a559b4d1b910e343ae0a5e4bebcea401027e9518c8cdba',
    's05_report_fixture': '93a1d575b0934c000c35efdacb3f76540c95fe50b5556fd6ee29cf0ea0f2d535',
    'auth_schedule': '9f72065d9cef2f6fd4f6b40e27f5971188b83cfd19faf0f65427728ef7f6197b',
}
WITNESS = '2b52d3c7125e465bd4b16fa8618fdb086ea79787d3ada469dfe68e82371d96f9'


def bind(assets, candidate, *, plan, graph, accepted_roots, catalogue_raw, lifecycle, trusted_connection,
         source_identity, business_day):
    paths = {name: assets / (name + '.py') for name in SOURCES}
    for name, path in paths.items():
        owning.exact(path, SOURCES[name])
    owning.exact(assets.parent / 'scope_witness.py', WITNESS)
    with owning.import_paths(assets):
        modules = {name: import_module(name) for name in SOURCES}
    owning.require(all(Path(module.__file__).absolute() == paths[name] for name, module in modules.items())
                   and Path(plan.__file__).absolute() == paths['auth_case_plan'],
                   'GLOBAL_AUTH_EXACT_CASE_MODULE_IMPORTS_REQUIRED')
    fixture = modules['s05_report_fixture']
    witness = import_module('scope_witness')
    owning.require(Path(witness.__file__).absolute() == assets.parent / 'scope_witness.py'
                   and fixture.capture is witness.capture, 'GLOBAL_AUTH_EXACT_SCOPE_OBSERVER_REQUIRED')
    route = modules['auth_schedule']
    native = modules['auth_credit_fixtures'].bind(candidate, plan=plan, exact_native_graph=graph,
                                                accepted_roots=accepted_roots)
    s05 = fixture.bind(assets, candidate, owner=owning, plan=plan, catalogue_raw=catalogue_raw,
                       relations=lifecycle.relations, trusted_connection=trusted_connection, identity_sql=route.DATABASE_ID)

    def capture_scope(cur):
        return lifecycle.provider._timezone_snapshot(cur, lock=False)

    return route.bind(plan=plan, native=native, credit=modules['credit_http'].bind(candidate),
                      s05=modules['s05_report_http'].bind(candidate, plan), prepare_s05=s05,
                      capture_scope=capture_scope, source_identity=source_identity, business_day=business_day)

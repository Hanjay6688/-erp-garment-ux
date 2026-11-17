"""Bind the retained ordinary transfer fixture across checked owning checkouts."""

from hashlib import sha256
from importlib import import_module
from pathlib import Path
import sys
from types import CodeType, FunctionType, ModuleType


PRIOR_SHA = '9fa73f327bd134b6b7eaee5e0d671759127c733200f3e5a69b9c9d684313fdcc'
SUPPORT_PINS = {
    'cp7_invoice_cases.py': 'a6b2e46346b211c0934b8b43f30d9ecfeb161ba37ab4eff5fdf7f183fc810bb1',
    'cp6_ao_ap_installed.py': 'c5ff9f51bfeaa04c95f1f77f8b82ce5129d93965ea4d452c867135e48a57bd62',
    'cp6_aa_invoice_partial_audit.py': 'aac0f1648806a108805591c40cb09ed4a1a78d4c16b5bdb93422d41582724578',
    'cp6_z_expanded_integrity_audit.py': 'c4f977bfd6dd9da1b1eaf068bddf6fce37296d016d4ff9832aa987640682042b',
    'cp7_finance_analysis_cases.py': 'b5698ef75c44aa093bf9093452b26408e0f50294e4acb17f381ae788d7c25872',
}


def require(value, reason):
    if not value:
        raise ValueError('OW06_TRANSFER_PAGE_' + reason)


def exact(path, digest):
    require(path.is_file() and not path.is_symlink(), 'REGULAR_SOURCE_REQUIRED:' + str(path))
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == digest, 'SOURCE_PIN_CHANGED:' + str(path))
    return raw


def verify_module(module, relative, roots, digest, functions):
    name = relative.removesuffix('.py').replace('/', '.')
    require(type(module) is ModuleType and sys.modules.get(name) is module and module.__name__ == name,
            'EXACT_NATURAL_MODULE_REQUIRED:' + name)
    path = Path(module.__file__)
    require(path.is_absolute() and path == path.resolve()
            and any(path == root / 'scripts' / relative for root in roots),
            'EXACT_NATURAL_SOURCE_PATH_REQUIRED:' + name + ':' + str(path))
    raw = exact(path, digest)
    origin = compile(raw, str(path), 'exec', dont_inherit=True)
    for name in functions:
        fn = getattr(module, name)
        expected = [code for code in origin.co_consts if type(code) is CodeType and code.co_name == name]
        require(type(fn) is FunctionType and fn.__globals__ is vars(module) and fn.__closure__ is None
                and fn.__code__.co_filename == str(path) and expected == [fn.__code__],
                'EXACT_NATURAL_FUNCTION_REQUIRED:' + relative + ':' + name)


def verify_fixture(pins, roots):
    cases = import_module('cp7_supplier_transfer.cases')
    single = cases.single
    invoice = single.invoice
    receipt = invoice.receipt
    prior = receipt.aa.prior
    graph = (
        (cases, 'cp7_supplier_transfer/cases.py', ('payload', 'read', 'command')),
        (single, 'cp7_supplier_payment_create_cases.py', ()),
        (single.supplier, 'cp7_supplier_payment_cases.py', ('physical_state',)),
        (receipt, 'cp7_procurement_cases.py', ('fixture', 'command', 'post')),
        (single.bc, 'cp6_bc_probe.py', ('fixture', 'tag', 'one')),
        (single.funding, 'cp7_cash_funding.py', ('fund', 'coa')),
        (single.misc, 'cp7_misc_cases.py', ('cash_balance', 'stock_cost')),
        (cases.auth, 'cp7_snapshot_cases.py', ('actor',)),
        (invoice, 'cp7_invoice_cases.py', ()),
        (cases.b.api, 'cp6_ao_ap_installed.py', ('admin',)),
        (receipt.aa, 'cp6_aa_invoice_partial_audit.py', ('at',)),
        (prior, 'cp6_z_expanded_integrity_audit.py', ('clone_material', 'set_open_period', 'set_zone', 'as_admin')),
        (single.misc.source, 'cp7_finance_analysis_cases.py', ('journal', 'fixture_journal_call')),
    )
    all_pins = pins | SUPPORT_PINS
    require(set(pins).isdisjoint(SUPPORT_PINS) and set(all_pins) == {relative for _, relative, _ in graph},
            'EXACT_FIXTURE_MANIFEST_REQUIRED')
    for module, relative, functions in graph:
        verify_module(module, relative, roots, all_pins[relative], functions)
    require(single.supplier.misc is single.misc and single.supplier.invoice is invoice
            and cases.auth is single.auth is receipt.auth is single.misc.source.auth
            and cases.b is single.b is receipt.b is cases.auth.b is single.misc.source.b
            and single.bc.api is cases.b.api and invoice.aa is receipt.aa and receipt.aa.zone is prior.set_zone,
            'EXACT_NATURAL_FIXTURE_ALIASES_REQUIRED')
    return cases


def bind(audit, base_path, *, accepted_roots):
    """Use owning's verified physical checkouts and keep the archived callback."""
    roots = tuple(Path(path) for path in accepted_roots)
    require(bool(roots) and len(roots) == len(set(roots))
            and all(path.is_absolute() and path == path.resolve() and (path / 'scripts').is_dir() for path in roots),
            'EXACT_ABSOLUTE_CHECKOUT_ROOTS_REQUIRED')
    base_path = Path(base_path).absolute()
    path = Path(__file__).absolute().with_name('transfer_page.py')
    original = ModuleType('ow06_pinned_transfer_page')
    original.__file__ = str(path)
    exec(compile(exact(path, PRIOR_SHA), str(path), 'exec', dont_inherit=True), vars(original))
    page = original.bind(audit, base_path)

    def fixture_sources():
        return verify_fixture(page.FIXTURE_PINS, roots)

    page.fixture_sources = fixture_sources
    return page

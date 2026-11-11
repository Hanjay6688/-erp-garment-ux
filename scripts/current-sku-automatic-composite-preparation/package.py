"""Complete owning engine with exact IO and actual Native25/browser2 counts."""
from contextlib import nullcontext
from pathlib import Path
import importlib.util
from hashlib import sha256
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from types import CodeType, MappingProxyType, ModuleType, SimpleNamespace
from uuid import UUID
import json
from json.encoder import encode_basestring
import math

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RETAINED = ROOT / 'scripts/current-sku-money-composite-preparation/package.py'
MANDOR_AUTHORITY = 'scripts/current-mandor-afui-preparation/report_io.py'
MANDOR_AUTHORITY_PIN = (9238, '300a4239a2e3fec6bbd6fa6fc8115a730034592aa362fee1993cff013e0c3c25')

# These are the three exact current-parent binding payloads. No financial
# state, catalogue field, parent proof or source declaration is projected out.
STATE_BINDINGS = (
    ('current_mandor_moving_for_money', 'cp7_sku_moving_average',
     'complete_current_parent', 'cp7.current-mandor-complete-state-binding.v1'),
    ('current_mandor_moving_money', 'cp7_sku_cost_components',
     'complete_current_moving_parent', 'cp7.current-mandor-moving-money-complete-state-binding.v1'),
    ('automatic_on_current_mandor_money', 'cp7_sku_automatic_pending',
     'complete_current_money_parent', 'cp7.current-automatic-complete-parent-state.v1'),
)


def state_value(value):
    """Lossless typed tree for a complete in-memory PostgreSQL parent state."""
    kind = type(value)
    if value is None:
        return ['null']
    if kind is bool:
        return ['bool', value]
    if kind is int:
        return ['int', str(value)]
    if kind is str:
        return ['str', value]
    if kind is float and math.isfinite(value):
        return ['float', value.hex()]
    if kind is Decimal and value.is_finite():
        parts = value.as_tuple()
        return ['decimal', parts.sign, list(parts.digits), parts.exponent]
    if kind is datetime:
        return ['datetime', value.isoformat(timespec='microseconds'), value.fold]
    if kind is date:
        return ['date', value.isoformat()]
    if kind is time:
        return ['time', value.isoformat(timespec='microseconds'), value.fold]
    if kind is timedelta:
        return ['timedelta', value.days, value.seconds, value.microseconds]
    if kind is UUID:
        return ['uuid', value.hex]
    if kind in (bytes, bytearray):
        return [kind.__name__, value.hex()]
    if kind in (dict, MappingProxyType):
        entries = [[state_value(key), state_value(item)] for key, item in value.items()]
        entries.sort(key=lambda entry: json.dumps(entry[0], ensure_ascii=False, separators=(',', ':')))
        return [kind.__name__, entries]
    if kind in (list, tuple):
        return [kind.__name__, [state_value(item) for item in value]]
    if kind in (set, frozenset):
        items = [state_value(item) for item in value]
        items.sort(key=lambda item: json.dumps(item, ensure_ascii=False, separators=(',', ':')))
        return [kind.__name__, items]
    raise TypeError('SKU_STATE_UNSUPPORTED_VALUE:' + kind.__name__)


def state_digest(value):
    digest = sha256()
    encoder = json.JSONEncoder(ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    pending = bytearray()
    strings = {}
    string_bytes = 0

    def emit(raw):
        pending.extend(raw)
        if len(pending) >= 64 * 1024:
            digest.update(pending)
            pending.clear()

    def encoded(item):
        return encoder.encode(state_value(item)).encode()

    def scalar(item):
        nonlocal string_bytes
        kind = type(item)
        if kind is str:
            raw = strings.get(item)
            if raw is None:
                raw = b'["str",' + encode_basestring(item).encode() + b']'
                # Catalogue copies repeat identifiers and function bodies.
                # Cache only immutable text, with both count and byte limits.
                if len(strings) < 8192 and string_bytes + len(raw) <= 24 * 1024 * 1024:
                    strings[item] = raw
                    string_bytes += len(raw)
            return raw
        if item is None:
            return b'["null"]'
        if kind is bool:
            return b'["bool",true]' if item else b'["bool",false]'
        if kind is int:
            return b'["int","' + str(item).encode('ascii') + b'"]'
        return encoded(item)

    containers = (dict, MappingProxyType, list, tuple, set, frozenset)

    def write(item):
        kind = type(item)
        if kind in (dict, MappingProxyType):
            emit(b'["' + kind.__name__.encode() + b'",[')
            keys = [(scalar(key), key) for key in item]
            keys.sort(key=lambda row: row[0])
            for index, (raw_key, key) in enumerate(keys):
                emit((b',[' if index else b'[') + raw_key + b',')
                write(item[key])
                emit(b']')
            emit(b']]')
        elif kind in (list, tuple):
            # Catalogue rows are short scalar lists. Encode those in one
            # pass while keeping the enclosing catalogue streaming.
            prefix = b'["' + kind.__name__.encode() + b'",['
            if len(item) <= 64 and all(type(member) not in containers for member in item):
                emit(prefix + b','.join(map(scalar, item)) + b']]')
                return
            emit(prefix)
            for index, member in enumerate(item):
                if index:
                    emit(b',')
                write(member)
            emit(b']]')
        elif kind in (set, frozenset):
            emit(b'["' + kind.__name__.encode() + b'",[')
            emit(b','.join(sorted(scalar(member) for member in item)))
            emit(b']]')
        else:
            emit(scalar(item))

    # Stream the same canonical typed bytes without materializing a second
    # tree for the entire chain of predecessor catalogues.
    emit(b'["cp7.complete-postgres-parent-state.v1",')
    write(value)
    emit(b']')
    digest.update(pending)
    return digest.hexdigest()


def bind_parent_state(product, observe=nullcontext):
    """Bind only derived SKU modules; leave the frozen catalogue unchanged."""
    money = product.parent()
    moving = money.parent()
    pending = []
    semantic_code = ('co_code', 'co_consts', 'co_names', 'co_varnames', 'co_freevars',
                     'co_cellvars', 'co_argcount', 'co_posonlyargcount',
                     'co_kwonlyargcount', 'co_nlocals', 'co_stacksize', 'co_flags')
    for module, (name, folder, payload, contract) in zip((moving, money, product), STATE_BINDINGS):
        expected_path = ROOT.parent / ('qualified-sku-automatic' if module is product else 'qualified-sku-money')
        expected_path = expected_path / 'scripts' / folder / 'composition.py'
        if type(module) is not ModuleType or module.__name__ != name or Path(module.__file__) != expected_path:
            raise ValueError('SKU_STATE_EXACT_DERIVED_MODULE_REQUIRED:' + name)
        source = ('def binding(catalog, prior, proof):\n'
                  '    return catalog.digest(dict(' + payload + '=prior, verified_parent_proof=proof,\n'
                  '                               contract=' + repr(contract) + '))\n')
        code = next(code for code in compile(source, str(expected_path), 'exec', dont_inherit=True).co_consts
                    if isinstance(code, CodeType))
        original = module.binding
        if (original.__globals__ is not module.__dict__ or original.__closure__ is not None
                or original.__defaults__ is not None or original.__kwdefaults__ is not None
                or any(getattr(original.__code__, field) != getattr(code, field) for field in semantic_code)):
            raise ValueError('SKU_STATE_UNCHANGED_COMPLETE_BINDING_REQUIRED:' + name)

        def bind(original):
            def binding(catalog, prior, proof):
                # The unchanged original selects every payload member. Only
                # its digest receives typed values; live state stays intact.
                with observe('SKU_COMPLETE_PARENT_STATE_DIGEST'):
                    return original(SimpleNamespace(digest=state_digest), prior, proof)
            return binding
        pending.append((module, bind(original)))
    # Validate all three before changing any private module.
    for module, binding in pending:
        module.binding = binding
    return dict(contract='cp7.complete-postgres-parent-state.v1', complete_binding_payloads=3,
                frozen_catalogue_and_financial_SQL_unchanged=True,
                typed_values_preserved=True, actual_ERP_cases=0, production_go=False)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def installer_authority(frozen_parent):
    path = frozen_parent / MANDOR_AUTHORITY
    if not path.is_file() or any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError('SKU_AUTOMATIC_EXACT_MANDOR_INSTALL_AUTHORITY_FILE_REQUIRED')
    raw = path.read_bytes()
    if (len(raw), sha256(raw).hexdigest()) != MANDOR_AUTHORITY_PIN:
        raise ValueError('SKU_AUTOMATIC_EXACT_MANDOR_INSTALL_AUTHORITY_BYTES_REQUIRED')
    return load('automatic_exact_mandor_install_authority', path).install_qualified_parent


def bind_install_authority(product, install_afui, as_admin, observe=nullcontext):
    money = product.parent()
    moving = money.parent()
    mandor = moving.parent()

    def install_parent(cur):
        # Mandor's fixture admission needs maintenance identity at entry.
        with observe('AFUI_PARENT_INSTALL'):
            afui_state = install_afui(cur)
        with observe('MANDOR_PARENT_DELTA'):
            mandor_state = mandor.install_delta(cur, afui_state)

        def install_sku_parents(admin):
            with observe('SKU_MOVING_PARENT_DELTA'):
                moving_state = moving.install_delta(admin, mandor_state)
            with observe('SKU_MONEY_PARENT_DELTA'):
                return money.install_delta(admin, moving_state)

        return as_admin(cur, install_sku_parents)

    def scoped(operation):
        def run(cur, state):
            return as_admin(cur, lambda admin: operation(admin, state))
        return run

    return dict(_sku_install_parent=install_parent,
                _sku_install_delta=scoped(product.install_delta),
                _sku_rollback_delta_preuse=scoped(product.rollback_delta_preuse),
                _sku_verify_installed=scoped(product.verify))


def derive(raw):
    original, prior = load('automatic_retained_whole_money_engine', RETAINED).derive(raw)
    io = load('automatic_complete_package_report_IO', HERE / 'report_io.py')
    text, output = io.derive_packet(original, 'money19')
    replacements = (
        ("'ACTUAL_CURRENT_MANDOR_AND_MOVING_PARENT_INSTALL',product.parent().install,cur",
         "'ACTUAL_CURRENT_MANDOR_MOVING_AND_MONEY_PARENT_INSTALL',_sku_install_parent,cur"),
        ("'FIRST_FINANCE_DELTA',product.install_delta,cur,prior",
         "'FIRST_FINANCE_DELTA',_sku_install_delta,cur,prior"),
        ("'FINANCE_DELTA_PREUSE_INVERSE',product.rollback_delta_preuse,cur,STATE",
         "'FINANCE_DELTA_PREUSE_INVERSE',_sku_rollback_delta_preuse,cur,STATE"),
        ("'SECOND_FINANCE_DELTA',product.install_delta,cur,prior",
         "'SECOND_FINANCE_DELTA',_sku_install_delta,cur,prior"),
        ("report['complete_installed_verification']=product.verify(cur,STATE)",
         "report['complete_installed_verification']=_sku_verify_installed(cur,STATE)"),
        ("'CURRENT_PARENT_SKU_MONEY_NATIVE19_ONLY'", "'CURRENT_PARENT_SKU_MONEY_AUTOMATIC_NATIVE25_BROWSER2_ONLY'"),
        ("report['actual_browser_cases']=0", "report['actual_browser_cases']=cases[runner.CASE]['actual_browser_cases']"),
        ("report['actual_business_cases']=cases[runner.CASE]['actual_Native_cases']",
         "report['actual_business_cases']=cases[runner.CASE]['actual_Native_cases']+cases[runner.CASE]['actual_browser_cases']\n"
         "            report['real_Auth_browser_claim']=cases[runner.CASE]['real_Auth_browser_claim']"),
    )
    for before, after in replacements:
        if text.count(before) != 1 or after in text:
            raise ValueError('SKU_AUTOMATIC_ONE_COMPLETE_PACKAGE_LABEL_ROUTE_REQUIRED')
        text = text.replace(before, after, 1)
    restored = text
    for before, after in reversed(replacements):
        restored = restored.replace(after, before, 1)
    restored = restored.replace(io.HELPER + '(OUT,report)', io.PACKET_BEFORE, 1)
    if restored != original:
        raise ValueError('SKU_AUTOMATIC_COMPLETE_OWNING_MONEY_PACKAGE_NOT_RECOVERED')
    compile(text, 'automatic-complete-owning-package', 'exec', dont_inherit=True)
    return text, dict(retained_money_package=prior, complete_packet_output=output,
                      additional_label_routes=2, actual_completed_browser_count_routes=2, complete_money_engine_recovered=True,
                      exact_install_authority_routes=5,
                      source_sha256=sha256(text.encode()).hexdigest(),
                      actual_counts_still_read_from_completed_component=True,
                      actual_Auth_HTTP_and_race_counts_remain_zero=True,
                      browser_count_and_Auth_claim_read_from_completed_current_component=True,
                      full_install_unused_inverse_used_guard_all22_all_rows_all_sequences_and_restore_unchanged=True,
                      actual_ERP_cases=0, production_go=False)

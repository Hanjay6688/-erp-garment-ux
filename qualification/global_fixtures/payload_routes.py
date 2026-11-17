"""Construct D1/E command arguments from a registered caller's public readbacks."""

import ast
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from types import CodeType, FunctionType, SimpleNamespace
from typing import TypedDict
from uuid import UUID

from auth_case_plan import D1_REVIEW_RPC, E_REVIEW_RPC, require


D1_CASES = 'scripts/cp7_credit_correction_de/cases.py'
E_CASES = 'scripts/cp7_credit_correction_de/e_cases.py'
NATIVE_FIXTURE = 'scripts/cp7_credit_correction_de/native_fixture.py'
CREDIT_APPLY = 'scripts/cp7_customer_credit/consumer/native_basic_cases.py'
PINS = {
    D1_CASES: 'c530bb87f72ee6091e032d15efdb2b2e55cf9c9632b64c9e781665b70325bbdb',
    E_CASES: '058a9c29b991b30ca4da6467cfeb2629179d3ce8f25b8dba09d6ea45f419e2ad',
    NATIVE_FIXTURE: '4fbe56583ffc63473c12195ddaae6ff3e0cd0ad46b358bf7eef7b5175c67e829',
    CREDIT_APPLY: '24ba3f79cc01905d1289b0db08552ed2c0593138e3c83f4551b88a025ae6a567',
}


class CommandArguments(TypedDict):
    p_payload: dict
    p_request: str
    p_expected: str


def original_function(raw, path, name, expected_names):
    module = ast.parse(raw, filename=str(path))
    function, = [node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == name]
    require(not function.decorator_list and not any(isinstance(node, (ast.Import, ast.ImportFrom))
                for node in ast.walk(function)), 'ONLY_RETAINED_TRANSFORMATION_SOURCE_REQUIRED')
    code, = (item for item in compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec',
                                      dont_inherit=True).co_consts if isinstance(item, CodeType))
    require(set(code.co_names) == expected_names and not code.co_freevars,
            'RETAINED_PAYLOAD_SOURCE_CLOSURE_CHANGED')
    return code


def checked_review(review, name, arguments):
    response = review(name, arguments)
    require(type(response) is dict and response.get('status') == 200 and type(response.get('body')) is dict,
            'PAYLOAD_REQUIRES_ACTUAL_PUBLIC_REVIEW_SUCCESS')
    return response['body']


def args_for(payload, version, request_id) -> CommandArguments:
    require(type(version) is str and bool(version) and type(request_id) is str
            and str(UUID(request_id)) == request_id, 'EXACT_VERSION_AND_REQUEST_UUID_REQUIRED')
    return dict(p_payload=payload, p_request=request_id, p_expected=version)


def bind(candidate):
    """Bind only the frozen pure transformations, with their reads injected."""
    code = {}
    for source, name, names in (
        (D1_CASES, 'payload', {'correction', 'workspace', 'len', 'dict'}),
        (E_CASES, 'intent', {'note', 'history', 'len', 'dict', 'sum', 'format', 'D'}),
    ):
        path = Path(candidate).absolute() / source
        require(path.is_file() and not any(part.is_symlink() for part in (path, *path.parents)),
                'REGULAR_RETAINED_PAYLOAD_SOURCE_REQUIRED')
        raw = path.read_bytes()
        require(sha256(raw).hexdigest() == PINS[source], 'RETAINED_PAYLOAD_SOURCE_CHANGED')
        code[name] = original_function(raw, path, name, names)

    def d1(review, *, sale_id, return_id, request_id) -> tuple[CommandArguments, dict]:
        def workspace(_cur, fixture, ident, *, subject, **query):
            require(fixture == {'sale': sale_id} and ident == return_id and subject is None
                    and query.keys() in (set(), {'proposed'}), 'EXACT_D1_REVIEW_ROUTE_REQUIRED')
            body = checked_review(review, D1_REVIEW_RPC, dict(p_query=dict(sale_id=sale_id, return_id=ident, **query)))
            require(body.get('source', {}).get('sale_id') == sale_id and body.get('document', {}).get('id') == return_id,
                    'D1_REVIEW_SOURCE_CHANGED')
            return body

        route = FunctionType(code['payload'], dict(__builtins__={'len': len, 'dict': dict},
                             correction=SimpleNamespace(workspace=workspace)))
        pair = {'source': {'f': {'sale': sale_id}}, 'initial_result': {'return_id': return_id}}
        payload, version, quote = route(None, pair, '250.00', None, None)
        require(quote.get('state') == 'READY' and quote.get('source_authority_proven') is True
                and type(quote.get('review_token')) is str and bool(quote['review_token']), 'D1_EXACT_READY_QUOTE_REQUIRED')
        return args_for(payload, version, request_id), quote

    def e(review, *, sale_id, request_id) -> tuple[CommandArguments, dict]:
        def history(_cur, ident, *, subject):
            require(ident == sale_id and subject is None, 'EXACT_E_REVIEW_ROUTE_REQUIRED')
            body = checked_review(review, E_REVIEW_RPC, dict(p_sale=ident))
            require(body.get('current_sale_id') == sale_id and body.get('current', {}).get('detail', {}).get('id') == sale_id,
                    'E_REVIEW_SOURCE_CHANGED')
            return body

        route = FunctionType(code['intent'], dict(__builtins__={'len': len, 'dict': dict, 'sum': sum, 'format': format},
                             note=SimpleNamespace(history=history), D=Decimal))
        payload, version, basis = route(None, {'target': {'sale': sale_id}}, '110.00', None)
        require(basis['issues'] == [] and basis['transfer_amount'] == '80.00'
                and payload['credit_carry_review']['replacement_net'] == '550.00'
                and payload['credit_carry_review']['remaining_amount'] == '470.00', 'E_EXACT_READY_CARRY_REQUIRED')
        return args_for(payload, version, request_id), basis

    return SimpleNamespace(d1=d1, e=e)

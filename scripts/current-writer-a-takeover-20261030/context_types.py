"""One reversible metadata-classifier correction; never grants row authority."""
from hashlib import sha256
from types import ModuleType
import ast

BEFORE = "        if column[2] != 'bigint':\n"
AFTER = ("        if any(row[2] not in ('bigint', 'xid8') for key, row in columns.items()\n"
         "               if key in ('transaction_id', 'txid')):\n")
PRIMARY_SOURCE = 'https://www.postgresql.org/docs/17/functions-info.html#FUNCTIONS-PG-SNAPSHOT'


def derive(source):
    if source.count(BEFORE) != 1 or AFTER in source:
        raise ValueError('GLOBAL_CONTEXT_EXACT_ONE_TYPE_ANCHOR_REQUIRED')
    current = source.replace(BEFORE, AFTER, 1)
    if current.replace(AFTER, BEFORE, 1) != source:
        raise ValueError('GLOBAL_CONTEXT_EXACT_REVERSE_REQUIRED')
    return current, dict(original_sha256=sha256(source.encode()).hexdigest(),
        derived_sha256=sha256(current.encode()).hexdigest(), counted_changes=1,
        exact_reverse=True, transaction_types=['bigint', 'xid8'],
        all_candidate_transaction_columns_checked=True, row_authority='UNKNOWN',
        ephemeral_or_permission_inference=False, primary_source=PRIMARY_SOURCE)


def classifier(source, *, corrected=True):
    text = derive(source)[0] if corrected else source
    tree = ast.parse(text)
    nodes = [x for x in tree.body if isinstance(x, ast.FunctionDef)
             and x.name in ('require', 'discover_contexts')]
    if sorted(x.name for x in nodes) != ['discover_contexts', 'require']:
        raise ValueError('GLOBAL_CONTEXT_EXACT_CLASSIFIER_REQUIRED')
    # Execute the complete original function, not a hand-rewritten projection.
    # Keep its original fail-closed helper and tuple of table relkinds.
    assignments = [x for x in tree.body if isinstance(x, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'TABLE_KINDS' for t in x.targets)]
    if len(assignments) != 1:
        raise ValueError('GLOBAL_CONTEXT_EXACT_TABLE_KINDS_REQUIRED')
    module = ModuleType('root_global_context_type_classifier')
    exec(compile(ast.Module(body=assignments + nodes, type_ignores=[]), '<exact-context-classifier>', 'exec'), module.__dict__)
    return module.discover_contexts

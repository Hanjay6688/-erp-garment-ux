"""Source-only OW04 trigger manifest proposal. No connection or SQL execution.

Build from the accepted P00 capture, the ordered CP6 package, the CURRENT
complete OW04 predecessor generator, and current OW04 table sources. The P00
capture is an explicit pinned input, never replaced by a fresh live capture.
"""
from __future__ import annotations
import argparse
from collections import Counter
import gzip
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

TABLES = tuple('erp.' + n for n in (
    'sales_headers', 'sales_payments', 'sales_returns',
    'fg_stock_movements', 'journal_entries', 'hpp_versions'))
P00_SHA = '274a0f8649ddb4d22887c65f7da1757a92e62e650fb572009af34194a960da2a'
ARCHIVE_SHA = '8f362635e8149f3c1ca254780a8601f7ff487ffa9e306816e1b836fd35765dd7'
CLONE_SOURCE_SHA = '861b23c0e7602fae4a83448080337f4857ded52deaf6301b4599a74aec5ca270'


def digest(value):
    return sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def masked(sql):
    """Preserve offsets, mask comments/literals/function bodies for DDL extraction.

    This is deliberately a small SOURCE grammar, not an arbitrary SQL parser.
    Unparsed selected-table REFERENCES are reported rather than silently used.
    """
    rx = re.compile(r"--[^\n]*|/\*.*?\*/|'(?:''|[^'])*'|\$(?:[A-Za-z_][A-Za-z_0-9]*)?\$", re.S)
    out = list(sql)
    pos = 0
    while m := rx.search(sql, pos):
        end = m.end()
        if m[0].startswith('$'):
            close = sql.find(m[0], end)
            if close < 0:
                raise ValueError('UNTERMINATED_SOURCE_DOLLAR_BODY')
            end = close + len(m[0])
        for i in range(m.start(), end):
            if out[i] != '\n':
                out[i] = ' '
        pos = end
    return ''.join(out)


def closing(text, start):
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                return i
    raise ValueError('UNTERMINATED_SOURCE_TABLE')


def parts(text):
    level = 0
    begin = 0
    for i, ch in enumerate(text):
        if ch == '(':
            level += 1
        elif ch == ')':
            level -= 1
        elif ch == ',' and level == 0:
            yield text[begin:i]
            begin = i + 1
    yield text[begin:]


def names(text):
    return [x.strip().strip('"').lower() for x in text.split(',')]


def foreign_key(relation, fragment, source, line):
    ref = re.search(r'\breferences\s+([\w]+\.[\w]+)(?:\s*\(([^)]*)\))?', fragment, re.I)
    if not ref:
        return None
    parent = ref[1].lower()
    if relation not in TABLES and parent not in TABLES:
        return None
    fk = re.search(r'\bforeign\s+key\s*\(([^)]*)\)', fragment, re.I)
    column = re.match(r'\s*(?:constraint\s+\w+\s+)?([\w]+)\s+', fragment, re.I)
    columns = names(fk[1]) if fk else [column[1].lower()] if column else None
    if not columns or columns[0] in {'constraint', 'foreign'}:
        raise ValueError('UNPARSED_SELECTED_FK_COLUMNS: ' + fragment)
    def action(kind):
        m = re.search(r'\bon\s+' + kind + r'\s+(no\s+action|restrict|cascade|set\s+null|set\s+default)', fragment, re.I)
        return {'no action': 'a', 'restrict': 'r', 'cascade': 'c', 'set null': 'n', 'set default': 'd'}[
            re.sub(r'\s+', ' ', m[1].lower()) if m else 'no action']
    # Every selected parent has actual id PK in the retained source. The
    # builder verifies that source precondition below; omitted REFERENCES
    # columns are resolved from that PK, not inferred from a live database.
    match = re.search(r'\bmatch\s+(full|partial|simple)', fragment, re.I)
    return dict(relation=relation, columns=columns, parent=parent,
        parent_columns=names(ref[2]) if ref[2] else ['id'],
        update_action=action('update'), delete_action=action('delete'),
        match_type={'full': 'f', 'partial': 'p', 'simple': 's'}[match[1].lower()] if match else 's',
        deferrable=bool(re.search(r'(?<!not )\bdeferrable\b', fragment, re.I)),
        initially_deferred=bool(re.search(r'initially\s+deferred', fragment, re.I)),
        validated=not bool(re.search(r'not\s+valid\b', fragment, re.I)),
        source=source, source_line=line, source_fragment=fragment.strip())


def fk_identity(row):
    return canonical({k: row[k] for k in (
        'relation', 'columns', 'parent', 'parent_columns', 'update_action',
        'delete_action', 'match_type', 'deferrable', 'initially_deferred', 'validated')})


def fk_extract(sql, source):
    visible = masked(sql)
    found = []
    for m in re.finditer(r'\bcreate\s+table\s+(?:if\s+not\s+exists\s+)?([\w]+\.[\w]+)\s*\(', visible, re.I):
        end = closing(visible, m.end() - 1)
        relation = m[1].lower()
        for fragment in parts(visible[m.end():end]):
            row = foreign_key(relation, fragment, source, visible[:m.start()].count('\n') + 1)
            if row:
                found.append(row)
    for m in re.finditer(r'\balter\s+table\s+(?:only\s+)?([\w]+\.[\w]+)\s+add\s+constraint\s+\w+\s+(foreign\s+key\b[^;]*);', visible, re.I):
        row = foreign_key(m[1].lower(), m[2], source, visible[:m.start()].count('\n') + 1)
        if row:
            found.append(row)
    return found


def function_body(definition):
    m = re.search(r'\bAS\s+(\$(?:[A-Za-z_]\w*)?\$)(.*?)\1', definition, re.S | re.I)
    if not m:
        raise ValueError('SOURCE_FUNCTION_BODY_MISSING')
    return m[2]


def source_function(sql, identity):
    m = list(re.finditer(r'\bcreate\s+(?:or\s+replace\s+)?function\s+' +
        re.escape(identity[:-2]) + r'\(\)\s*returns\s+trigger\b.*?\bas\s+(\$(?:[A-Za-z_]\w*)?\$)(.*?)\1', sql, re.I | re.S))
    if len(m) != 1:
        raise ValueError('SOURCE_TRIGGER_FUNCTION_NOT_UNIQUE: ' + identity)
    return m[0][0], m[0][2]


def fresh_trigger_acl(sql, identity, owner):
    # Closed fresh trigger set, derived from its actual ownership/grant source.
    # Installment's owner loop transfers to its read role, then the existing
    # explicit schema-wide grant additionally authorizes postgres. Neither
    # permission is learned from a live mismatch or installed by this builder.
    principals={owner}
    if identity=='cp7_installment.guard_journal()':
        clause=r'\bgrant\s+execute\s+on\s+all\s+functions\s+in\s+schema\s+cp7_installment\s+to\s+postgres\s*;'
        if len(re.findall(clause,masked(sql),re.I))!=1:
            raise ValueError('SOURCE_INSTALLMENT_POSTGRES_EXECUTE_GRANT_CHANGED')
        principals.add('postgres')
    return sorted([dict(grantee=p,grantable=False,privilege='EXECUTE')for p in principals],key=canonical)


def attachment(definition, source, owner='postgres'):
    # Controlled source set: ordinary row triggers, no WHEN/ARGS/transition
    # tables/constraints. Refuse grammar expansion instead of normalizing it.
    m = re.fullmatch(r'CREATE TRIGGER (\w+) (BEFORE|AFTER) (.+?) ON (\w+\.\w+) FOR EACH ROW EXECUTE FUNCTION (\w+\.\w+\(\))', definition, re.I)
    if not m:
        raise ValueError('UNSUPPORTED_SOURCE_TRIGGER_GRAMMAR: ' + definition)
    events = m[3].upper()
    columns = []
    if 'UPDATE OF ' in events:
        columns = names(events.split('UPDATE OF ', 1)[1])
    typ = 1 + (2 if m[2].upper() == 'BEFORE' else 0)
    typ += sum(bit for word, bit in (('INSERT', 4), ('DELETE', 8), ('UPDATE', 16), ('TRUNCATE', 32)) if word in events)
    return dict(relation=m[4].lower(), name=m[1], function=m[5].lower(), enabled='O', internal=False,
        trigger_type=typ, argument_count=0, args_hex='', columns=columns,
        deferrable=False, initially_deferred=False, condition=None,
        old_table=None, new_table=None, constraint=None, parent_trigger=None,
        referenced_relation=None, relation_owner=owner, definition=definition,
        definition_sha256=digest(definition), source=source)


def build(repo, p00_path, archive_path):
    p00_bytes = p00_path.read_bytes()
    if digest(p00_bytes) != P00_SHA or digest(archive_path.read_bytes()) != ARCHIVE_SHA:
        raise ValueError('ACCEPTED_STATIC_INPUT_PIN_CHANGED')
    p00 = json.loads(gzip.decompress(p00_bytes))
    with zipfile.ZipFile(archive_path) as z:
        base = z.read('CLONE_install.source-erp.sql')
    if digest(base) != CLONE_SOURCE_SHA:
        raise ValueError('ACCEPTED_BASE_SOURCE_PIN_CHANGED')
    base = base.decode()
    for table in TABLES:
        name = table.split('.')[1]
        if not re.search(r'ALTER TABLE ONLY ' + re.escape(table) + r'\s+ADD CONSTRAINT \w+ PRIMARY KEY \(id\)', base):
            raise ValueError('SELECTED_PARENT_ID_PK_SOURCE_NOT_PROVEN: ' + name)

    # This process only evaluates existing SQL generators. Trap constructors
    # first. No connection, installer, SQL execution, or privileged call exists.
    import psycopg
    def no_database(*args, **kwargs):
        raise RuntimeError('TRIGGER_PROPOSAL_DATABASE_FORBIDDEN')
    psycopg.connect = no_database
    psycopg.Connection.connect = no_database
    psycopg.AsyncConnection.connect = no_database
    old_bytes = Path.read_bytes
    missing = repo / 'docs/cp7/evidence/p00/CP7_P00_CATALOGUE.json.gz'
    Path.read_bytes = lambda path: p00_bytes if path == missing else old_bytes(path)
    try:
        sys.path.insert(0, str(repo / 'scripts'))
        import cp7_f05_analysis_probe as pre
        sql = '\n'.join((pre.p09.bundle.bundle(), pre.f03.extension(), pre.planning.extension(),
            pre.baseline.extension(), pre.supply.extension(), pre.schedule.extension(),
            pre.bundle.predecessor.extension(), pre.bundle.extension()))
    finally:
        Path.read_bytes = old_bytes
    credit = repo / 'scripts/cp7_customer_credit'
    spec = importlib.util.spec_from_file_location('trigger_proposal_owning', credit/'integration/owning_bundle.py')
    owning = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owning)
    adm_spec = importlib.util.spec_from_file_location('trigger_proposal_admission', credit/'admission/03_native_admission_transform.py')
    admission = importlib.util.module_from_spec(adm_spec)
    sys.modules[adm_spec.name] = admission
    adm_spec.loader.exec_module(admission)

    relevant = [t for t in p00['triggers'] if t['schema'] + '.' + t['relation'] in TABLES]
    expected = [attachment(t['definition'], 'accepted_P00_catalogue') for t in relevant]
    fn_ids = {t['function'] for t in relevant}
    fns = []
    for item in p00['functions']:
        if item['signature'] not in fn_ids:
            continue
        if digest(item['definition']) != item['definition_sha256']:
            raise ValueError('P00_DEFINITION_PIN_NOT_SELF_CONSISTENT')
        if re.search(r'\b' + re.escape(item['name']) + r'\s*\(', masked(sql)):
            raise ValueError('PREDECESSOR_TRIGGER_TARGET_HAS_UNREVIEWED_DELTA: ' + item['signature'])
        body = function_body(item['definition'])
        fns.append(dict(identity=item['signature'], owner=item['owner'], language=item['language'],
            security_definer=item['security_definer'], volatility=item['volatility'], config=item['settings'],
            acl=sorted(item['acl'], key=canonical), result='trigger', input_arguments='',
            body_sha256=digest(body), definition_sha256=item['definition_sha256'],
            source='accepted_P00_catalogue', source_definition=item['definition']))

    fresh = (
        ('cp7_installment.guard_journal()', 'scripts/cp7-src/payroll/installments.sql', 'cp7_installment_read'),
        ('cp7_kasbon.guard_journal()', 'scripts/cp7-src/payroll/kasbon.sql', 'postgres'),
        ('cp7_cutover.guard_journal()', 'scripts/cp7-src/cutover/cutover.sql', 'postgres'),
        ('cp7_cutover.guard_movement()', 'scripts/cp7-src/cutover/cutover.sql', 'postgres'),
    )
    for identity, file, owner in fresh:
        source_text=(repo/file).read_text()
        fragment, body = source_function(source_text, identity)
        if sql.count(fragment) != 1:
            raise ValueError('FRESH_TRIGGER_SOURCE_NOT_IN_EXACT_PREDECESSOR: ' + identity)
        fns.append(dict(identity=identity, owner=owner, language='plpgsql', security_definer=True,
            volatility='v', config=['search_path=""'], acl=fresh_trigger_acl(source_text,identity,owner),
            result='trigger', input_arguments='', body_sha256=digest(body), definition_sha256=None,
            source=file, source_definition=fragment, source_definition_sha256=digest(fragment)))
    for m in re.finditer(r'\bcreate\s+trigger\s+[^;]*?\bon\s+(erp\.\w+)\b[^;]*;', masked(sql), re.I | re.S):
        if m[1].lower() not in TABLES:
            continue
        # Trigger DDL has no literals in this closed set. Canonical PG order.
        text = re.sub(r'\s+', ' ', m[0].strip().rstrip(';'))
        head = re.fullmatch(r'create trigger (\w+) (before|after) (.+?) on (erp\.\w+) for each row execute function (\w+\.\w+\(\))', text, re.I)
        if not head:
            raise ValueError('UNREVIEWED_PREDECESSOR_ATTACHMENT_GRAMMAR')
        events = ' OR '.join(word for word in ('INSERT', 'DELETE', 'UPDATE') if word in head[3].upper())
        definition = f'CREATE TRIGGER {head[1]} {head[2].upper()} {events} ON {head[4]} FOR EACH ROW EXECUTE FUNCTION {head[5]}'
        expected.append(attachment(definition, 'current_complete_predecessor_generator'))
    if len(expected) != 25 or len(fns) != 18:
        raise ValueError('LOCKED_SOURCE_TRIGGER_CENSUS_CHANGED')
    pre_fns = sorted(fns, key=lambda x: x['identity'])
    composed_fns = json.loads(json.dumps(pre_fns))
    target = next(f for f in composed_fns if f['identity'] == 'erp.sync_opening_hpp_after_return_status()')
    old_body = function_body(target['source_definition'])
    changed = admission.opening_return_status(old_body)
    target['source_definition'] = target['source_definition'].replace(old_body, changed, 1)
    target['definition_sha256'] = digest(target['source_definition'])
    target['body_sha256'] = digest(changed)
    target['source'] = 'current_exact_OW04_admission.opening_return_status(accepted_P00_definition)'

    package_manifest = json.loads((repo / 'supabase/release/cp6-t3/MANIFEST.json').read_text())
    stages = [('accepted_base_clone_dump', base)] + [(f['file'], (repo / f['file']).read_text()) for f in package_manifest['files']]
    stages.append(('current_complete_predecessor_generator', sql))
    keys = {}
    for source, text in stages:
        for fk in fk_extract(text, source):
            keys[fk_identity(fk)] = fk
    predecessor_fks = sorted(keys.values(), key=fk_identity)
    for name in owning.SQL_FILES:
        for fk in fk_extract((credit / name).read_text(), 'scripts/cp7_customer_credit/' + name):
            keys[fk_identity(fk)] = fk
    composed_fks = sorted(keys.values(), key=fk_identity)
    empty_fks = dict(keys)
    for name in ('native-empty/01_native_empty_facts.sql', 'native-empty/02_native_empty_callbacks.sql', 'native-empty/04_exact_overlays.sql'):
        for fk in fk_extract((credit/name).read_text(), 'scripts/cp7_customer_credit/' + name):
            empty_fks[fk_identity(fk)] = fk

    pins = {f['file']: digest((repo / f['file']).read_bytes()) for f in package_manifest['files']}
    for path in [repo/'supabase/release/cp6-t3/MANIFEST.json', repo/'scripts/cp7_ow04_probe.py',
        credit/'integration/owning_bundle.py', credit/'admission/03_native_admission_transform.py'] + [repo/f[1] for f in fresh] + [credit/n for n in owning.SQL_FILES] + [credit/'native-empty/01_native_empty_facts.sql']:
        pins[str(path.relative_to(repo))] = digest(path.read_bytes())
    for module in list(sys.modules.values()):
        path = Path(getattr(module, '__file__', '') or '/__none__').resolve()
        if path.is_relative_to(repo) and path.is_file() and path.suffix == '.py':
            pins[str(path.relative_to(repo))] = digest(path.read_bytes())
    return dict(format='OW04_BOUNDED_TRIGGER_SOURCE_PINS_PROPOSAL_V1', classification='STATIC_SOURCE_DERIVED_NOT_NATIVE_EXECUTION',
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
        database_calls=0, tables=list(TABLES), accepted_P00=dict(path=str(p00_path), sha256=P00_SHA,
        accepted_base=p00['accepted_base'], runtime=p00['runtime']),
        accepted_base_clone=dict(path=str(archive_path), archive_sha256=ARCHIVE_SHA, entry_sha256=CLONE_SOURCE_SHA),
        generated_predecessor_sha256=digest(sql), repository_source_pins=dict(sorted(pins.items())),
        ordinary_triggers=sorted(expected, key=lambda x: (x['relation'], x['name'])),
        phases={
            'VERIFIED_PREDECESSOR': dict(functions=pre_fns, foreign_keys=predecessor_fks),
            'OW04_COMPOSED': dict(functions=composed_fns, foreign_keys=composed_fks),
            'OW04_COMPOSED_NATIVE_EMPTY': dict(functions=composed_fns, foreign_keys=sorted(empty_fks.values(), key=fk_identity)),
        }, limits=[
            'Static FK extractor covers direct CREATE TABLE / ALTER TABLE ADD CONSTRAINT FK grammar in reviewed source; does not certify arbitrary dynamic SQL.',
            'Canonical pg_get_functiondef SHA is not guessed for four new CP7 functions. Initial acceptance pins exact prosrc plus signature/language/owner/security/volatility/config/ACL, then freezes full live definition for unchanged-after equality.',
            'Use existing exact complete predecessor verification and immutable Native source pins; this bounded guard is not a complete ERP call graph or a replacement for actual B/N/Z proof.',
            'The P00 capture excludes internal triggers; internal attachments are derived from source-owned FK semantics, never approved from first live capture.',
        ])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--p00-catalog', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.repo.resolve(), args.p00_catalog.resolve(), args.archive.resolve())
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(canonical(dict(output=str(args.out), sha256=digest(args.out.read_bytes()),
        ordinary_triggers=len(result['ordinary_triggers']), functions=len(result['phases']['OW04_COMPOSED']['functions']),
        foreign_keys={phase: len(v['foreign_keys']) for phase, v in result['phases'].items()}, database_calls=0)))

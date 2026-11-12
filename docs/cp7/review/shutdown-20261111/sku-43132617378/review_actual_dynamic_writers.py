"""Inspect the exact A165 diagnostic catalogue for the two dynamic writer candidates."""
from hashlib import sha256
from pathlib import Path
import json
import re
import sys

from pglast import ast, parse_sql


MIGRATION = 'erp._validate_migration_batch_base(uuid)'
PREPAY = 'erp.manage_initial_prepayment_v1(jsonb)'
PERMISSION = 'erp.has_permission(text)'
CATALOGUE = 'a90c17fc625cfca373da74c588c165b26fafde21d3b51a1b62228c582ab6677f'


def parsed(template, *values):
    query = template.replace("''", "'")
    for value in values:
        assert re.fullmatch(r'[a-z_][a-z_0-9]*', value)
        query = query.replace('%I', '"' + value + '"', 1)
    assert '%I' not in query
    parsed_sql = parse_sql(query)
    assert len(parsed_sql) == 1
    return parsed_sql[0].stmt


def migration_routes(source, relations, columns):
    first = source.split('for ref in select * from(values', 2)[1].split(') fields(entity,relation_name,field_names)', 1)[0]
    second = source.split('for ref in select * from(values', 2)[2].split(') refs(field,relation_name,code_field', 1)[0]
    casts = re.findall(r"\('[A-Z_]+','([a-z_]+)',array\[", first)
    references = re.findall(r"\('[a-z_]+','([a-z_]+)','([a-z_]+)',", second)
    templates = re.findall(r"execute format\('((?:[^']|'')*)'", source, re.I)
    assert len(casts) == 16 and len(references) == 12 and len(templates) == 3
    assert templates[0] == templates[1] == 'select jsonb_populate_record(null::erp.%I,$1)'
    for relation in casts:
        assert 'erp.' + relation in relations
        assert isinstance(parsed(templates[0], relation), ast.SelectStmt)
    for relation, code in references:
        assert 'erp.' + relation in relations
        assert ('erp.' + relation, code) in columns
        assert isinstance(parsed(templates[2], relation, code), ast.SelectStmt)
    return dict(templates=templates, typed_read_relations=sorted('erp.' + n for n in casts),
                lookup_columns=sorted(f'erp.{r}.{c}' for r, c in references),
                direct_dynamic_dml=0, retains_static_batch_updates=True)


def prepayment_routes(source, relations, functions, watched):
    fields = ('table', 'parent', 'fk', 'link', 'rpc')
    selectors = {}
    for field in fields:
        match = re.search(r"v_" + field + r":=case a\.party_type when 'SUPPLIER' then '([a-z_]+)' "
                          r"when 'CUSTOMER' then '([a-z_]+)' else '([a-z_]+)' end;", source)
        assert match, field
        selectors[field] = match.groups()
    opening = dict(re.findall(r"v_(table|parent|fk|link|rpc):='([a-z_]+)'", source))
    assert len(opening) == len(fields)
    assert all(source.count(f"v_{key}:='{value}'") == 2 for key,value in opening.items())
    routes = {key: dict(zip(fields, vals, strict=True))
              for key,vals in zip(('SUPPLIER','CUSTOMER','VENDOR'), zip(*selectors.values(), strict=True), strict=True)}
    routes['OPENING'] = opening
    templates = re.findall(r"execute format\('((?:[^']|'')*)'", source, re.I)
    assert len(templates) == 6
    assert "if v_link='opening_settlement_id' then" in source
    assert "insert into erp.opening_subledger_settlements(" in source
    for name, row in routes.items():
        table, parent, fk, link, rpc = (row[k] for k in fields)
        assert {'erp.' + table, 'erp.' + parent, 'erp.initial_import_prepayment_payments'} <= relations
        assert isinstance(parsed(templates[0], table), ast.SelectStmt)
        assert isinstance(parsed(templates[1], parent), ast.SelectStmt)
        if name != 'OPENING':
            assert isinstance(parsed(templates[2], table, fk, table), ast.InsertStmt)
        assert isinstance(parsed(templates[3], link), ast.InsertStmt)
        post, reverse = f'erp.post_{rpc}(uuid)', f'erp.reverse_{rpc}(uuid,text)'
        assert {post,reverse} <= functions, (name, post, reverse)
        assert isinstance(parsed(templates[4], 'post_' + rpc), ast.SelectStmt)
        assert isinstance(parsed(templates[5], 'reverse_' + rpc), ast.SelectStmt)
        row.update(post=post, reverse=reverse, table_in_existing_lower_bound='erp.' + table in watched,
                   parent_in_existing_lower_bound='erp.' + parent in watched)
    return dict(templates=templates, routes=routes, selection_from_catalogued_party_and_opening=True,
                runtime_replay_required=True)


def direct_private_permission_calls(catalogue):
    functions, schemas, roles = (dict(catalogue[k]) for k in ('functions','schemas','roles'))
    inherits = {}
    for signature, row in catalogue['memberships']:
        role, member, _ = signature.split(':', 2)
        if row[1]:
            inherits.setdefault(member,set()).add(role)

    def allows(role, signature):
        if roles[role][0]:
            return True
        grants, pending = {role,'PUBLIC'}, [role]
        while pending:
            for other in inherits.get(pending.pop(), ()):
                if other not in grants:
                    grants.add(other)
                    pending.append(other)
        return (any(a[0] in grants and a[2]=='EXECUTE' for a in functions[signature][-1])
                and any(a[0] in grants and a[2]=='USAGE' for a in schemas[signature.split('.')[0]][1]))

    ref = re.compile(r'\b"?erp"?\s*\.\s*"?has_permission"?\s*\(', re.I)
    direct = [sig for sig,row in functions.items() if sig != PERMISSION and ref.search(row[0])]
    exposed = [sig for sig in direct if allows('authenticated', sig)]
    ungranted = [sig for sig in exposed if not functions[sig][4] or not allows(functions[sig][1], PERMISSION)]
    return dict(functions_examined=len(functions), qualified_direct_references=len(direct),
                authenticated_has_private_execute=allows('authenticated', PERMISSION),
                authenticated_exposed_direct=exposed, exposed_direct_with_missing_grant=ungranted)


def main():
    raw = Path(sys.argv[1]).read_bytes()
    assert sha256(raw).hexdigest() == CATALOGUE
    cat = json.loads(raw)
    assert len(cat) == 25
    f, r = (dict(cat[name]) for name in ('functions','relations'))
    columns = {tuple(n.rsplit(':',1)) for n,_ in cat['columns']}
    watched = set(json.loads(Path(sys.argv[2]).read_bytes())['required_relation_lower_bound'])
    assert len(watched) == 276
    sources = {name:f[name][0] for name in (MIGRATION,PREPAY)}
    result = dict(status='A165_DIAGNOSTIC_OFFLINE_ACTUAL_DYNAMIC_WRITER_SOURCE_REVIEW',
                  run_id=43105533441, artifact_id=13902367418, catalogue_sha256=CATALOGUE,
                  source_sha256={name:sha256(src.encode()).hexdigest() for name,src in sources.items()},
                  migration=migration_routes(sources[MIGRATION],r,columns),
                  prepayment=prepayment_routes(sources[PREPAY],set(r),set(f),watched),
                  direct_permission=direct_private_permission_calls(cat),
                  actual_ERP_cases=0, runtime_admission=False, production_go=False)
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()

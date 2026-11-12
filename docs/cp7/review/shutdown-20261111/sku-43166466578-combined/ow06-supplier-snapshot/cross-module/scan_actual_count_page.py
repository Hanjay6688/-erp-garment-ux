from collections import Counter
from hashlib import sha256
import json,re,sys
from pathlib import Path
from zipfile import ZipFile
from pglast import ast,parse_plpgsql,parse_sql

def descendants(node,kind):
    if isinstance(node,kind):
        yield node
    if isinstance(node,ast.Node):
        for name in node:
            yield from descendants(getattr(node,name),kind)
    elif isinstance(node,(list,tuple)):
        for child in node:
            yield from descendants(child,kind)

def execsql(node):
    if isinstance(node,list):
        for value in node:yield from execsql(value)
    elif isinstance(node,dict):
        for k,value in node.items():
            if k=='PLpgSQL_stmt_execsql':
                yield value['lineno'],value['sqlstmt']['PLpgSQL_expr']['query']
            else:
                yield from execsql(value)

def relation_names(tree):
    return {f'{r.schemaname}.{r.relname}' if r.schemaname else r.relname
            for r in descendants(tree,ast.RangeVar)}

def direct_count(node):
    return isinstance(node,ast.SelectStmt) and any(
        isinstance(field.val,ast.FuncCall)
        and field.val.funcname[-1].sval.lower()=='count' for field in node.targetList or ())

archive=Path(sys.argv[1]);output=Path(sys.argv[2])
with ZipFile(archive) as z:
    raw=z.read('SKU_GLOBAL_PARENT_ACTUAL_FULL25.json')
assert sha256(raw).hexdigest()=='5ff582717522b766c12024c1bf3299066475f14a3c6021a3543f378f829e0c07'
functions=dict(json.loads(raw)['functions'])
groups=Counter();findings=[];unparsed=[]
for signature,row in functions.items():
    code,owner,language,_,_,_,_,_,volatility,*_=row
    if not re.match(r'^(?:public|erp|cp7_\w+)\.',signature):
        continue
    groups['erp_visible_function_rows']+=1
    if language!='plpgsql' or volatility!='v' or not re.search(r'\bcount\s*\(',code,re.I) or not re.search(r'\boffset\b',code,re.I):
        continue
    groups['volatile_plpgsql_count_and_offset_candidates']+=1
    try:
        parsed=parse_plpgsql(code)
    except Exception as exc:
        unparsed.append(dict(signature=signature,stage='plpgsql',error=str(exc).splitlines()[0]))
        continue
    queries=[]
    for line,query in execsql(parsed):
        try:
            sqls=parse_sql(query)
        except Exception as exc:
            unparsed.append(dict(signature=signature,line=line,stage='sql',error=str(exc).splitlines()[0]))
            continue
        for s in sqls:
            if not isinstance(s.stmt,ast.SelectStmt):continue
            queries.append((line,s.stmt,relation_names(s.stmt)))
    groups['candidate_functions_parsed']+=1
    for line,query,relations in queries:
        if not direct_count(query):continue
        for following,data,rel in queries:
            if following<=line or not (relations&rel):continue
            if not any(stmt.limitOffset is not None for stmt in descendants(data,ast.SelectStmt)):continue
            findings.append(dict(signature=signature,count_line=line,page_line=following,shared_relations=sorted(relations&rel),
                                 function_sha256=sha256(code.encode()).hexdigest()))

result=dict(status='ACTUAL_ERP_CATALOGUE_SEPARATE_COUNT_PAGE_SCAN',source_archive=archive.name,
            catalogue_sha256=sha256(raw).hexdigest(),all_function_rows=len(functions),counts=dict(groups),
            candidates=findings,unparsed=unparsed,read_only=True,actual_erp_cases=0)
output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('status','all_function_rows','counts','candidates','unparsed')}))


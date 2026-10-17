"""Flag plpgsql variables (and parameters) that are also used as table/function aliases in the same function body: such a
clash fails only at run time with "column reference ... is ambiguous" (CI 39002828381; docs/ERP_BEST_PRACTICES.md E25c)."""
import re,sys
t=open(sys.argv[1]).read()
fn_re=re.compile(r"create (?:or replace )?function ([a-z_0-9.]+)\((.*?)\)\s*returns.*?language plpgsql.*?as \$([a-z_0-9]*)\$(.*?)\$\3\$",re.S|re.I)
n=0
for name,args,_,src in fn_re.findall(t):
    n+=1
    decl=src.split('begin',1)[0]
    vars_=set(re.findall(r"(?:^|[;,\s])([a-z_][a-z_0-9]*)\s+(?:erp\.|cp7_|jsonb|text|uuid|integer|bigint|numeric|boolean|timestamptz|record|constant)",decl))
    vars_|=set(a.split()[0] for a in args.split(',') if a.strip())
    body=src.split('begin',1)[1] if 'begin' in src else src
    aliases=set(re.findall(r"\)\s*([a-z_][a-z_0-9]*)\b(?=\s*(?:where|on\b|cross|left|join|with|\)|order|,|$|loop))",body))
    aliases|=set(re.findall(r"(?:from|join)\s+(?:erp|cp7_[a-z_]+)\.[a-z_0-9]+\s+([a-z_][a-z_0-9]*)",body))
    aliases-= {'where','on','order','join','left','cross','with','loop','limit','and','or','for','then','end','group','as','into','union','select','set','values','returning'}
    clash=vars_&aliases
    if clash:print(name,sorted(clash))
print('functions',n)

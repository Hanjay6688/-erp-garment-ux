import re,sys,pathlib
# usage: extract_fn.py <file> <fn_name> [fn_name...]  prints last definition of each fn in file with line numbers
path=pathlib.Path(sys.argv[1]); names=sys.argv[2:]
lines=path.read_text(errors='replace').split('\n')
for nm in names:
    pat=re.compile(r'^\s*create\s+(or\s+replace\s+)?function\s+(erp|public)\.'+re.escape(nm)+r'\s*\(',re.I)
    starts=[i for i,l in enumerate(lines) if pat.match(l)]
    if not starts:
        print(f'### {nm}: NOT FOUND in {path}'); continue
    s=starts[-1]
    # find end: first line after s matching ^\$[a-z_]*\$\s*; (dollar quote close) possibly followed by language
    end=None
    tag=None
    for j in range(s,min(s+40,len(lines))):
        m=re.search(r'as\s+(\$[A-Za-z_]*\$)',lines[j],re.I)
        if m: tag=m.group(1); break
    if tag is None: tag='$function$'
    for j in range(s+1,len(lines)):
        if lines[j].strip().startswith(tag) and lines[j].strip().rstrip(';').strip()==tag:
            end=j; break
        if re.match(r'^\s*'+re.escape(tag)+r'\s*(language\s+\w+\s*)?;?\s*$',lines[j],re.I):
            end=j; break
    if end is None: end=min(s+400,len(lines)-1)
    print(f'### {nm} @ {path}:{s+1}-{end+1}')
    for j in range(s,end+1):
        print(f'{j+1:6d}\t{lines[j]}')
    print()

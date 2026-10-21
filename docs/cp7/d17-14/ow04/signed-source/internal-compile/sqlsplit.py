import re

def split_sql(s):
    out=[];start=0;i=0;quote=None;block=0
    while i<len(s):
        if quote:
            if quote in ("'",'"'):
                if s.startswith(quote+quote,i):i+=2;continue
                if s[i]==quote:quote=None
                elif s[i]=="\\" and quote=="'":i+=1
                i+=1;continue
            if s.startswith(quote,i):i+=len(quote);quote=None
            else:i+=1
            continue
        if block:
            if s.startswith('/*',i):block+=1;i+=2
            elif s.startswith('*/',i):block-=1;i+=2
            else:i+=1
            continue
        if s.startswith('--',i):
            n=s.find('\n',i);i=len(s) if n<0 else n+1;continue
        if s.startswith('/*',i):block=1;i+=2;continue
        if s[i] in ("'",'"'):quote=s[i];i+=1;continue
        if s[i]=='$':
            m=re.match(r'\$[A-Za-z_0-9]*\$',s[i:])
            if m:quote=m.group();i+=len(quote);continue
        if s[i]==';':
            out.append(s[start:i+1]);start=i+1
        i+=1
    if s[start:].strip():out.append(s[start:])
    return out

def clean_start(s):
    while True:
        old=s;s=s.lstrip()
        if s.startswith('--'):s=s[s.find('\n')+1:]
        elif s.startswith('/*'):s=s[s.find('*/')+2:]
        if s==old:return s

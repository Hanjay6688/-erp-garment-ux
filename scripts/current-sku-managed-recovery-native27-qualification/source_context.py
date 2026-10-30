"""Exact public source-proof DB guard, no product/runtime globals patched."""
from contextlib import contextmanager
from hashlib import sha256
import ast
import importlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PATH='scripts/current-sku-recovery-material-lock/runtime_source.py'


@contextmanager
def fenced_source_read():
    source=json.loads((ROOT/'scripts/current-sku-recovery-material-lock/SOURCE.json').read_bytes())
    raw=(ROOT/PATH).read_bytes();pin=source['files'][PATH]
    assert len(raw)==pin['bytes']and sha256(raw).hexdigest()==pin['sha256'],'SKU27_PUBLIC_DB_GUARD_SOURCE_CHANGED'
    tree=ast.parse(raw);functions=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='database_guard']
    assert len(functions)==1,'SKU27_EXACT_PUBLIC_DB_GUARD_REQUIRED'
    namespace=dict(contextmanager=contextmanager,importlib=importlib)
    exec(compile(ast.Module(body=functions,type_ignores=[]),str(ROOT/PATH),'exec'),namespace)
    attempts=[];controls=[];other_attempts=[];active=True
    def audit(event,args):
        if not active:return
        if event in('socket.connect','socket.getaddrinfo','urllib.Request','http.client.connect'):
            other_attempts.append(event);raise RuntimeError('SKU27_SOURCE_NETWORK_FORBIDDEN:'+event)
        if event=='subprocess.Popen'and(Path(str(args[0])).name!='git'or not args[1]or Path(str(args[1][0])).name!='git'):
            other_attempts.append('non_git_subprocess');raise RuntimeError('SKU27_SOURCE_NON_GIT_SUBPROCESS_FORBIDDEN')
    sys.addaudithook(audit)
    try:
        with namespace['database_guard'](attempts,controls):
            yield dict(attempts=attempts,self_controls=controls,network_nonGit_attempts=other_attempts,
                       public_source_sha256=pin['sha256'])
        assert not attempts and not other_attempts,('SKU27_SOURCE_FORBIDDEN_ATTEMPTS',attempts,other_attempts)
    finally:active=False

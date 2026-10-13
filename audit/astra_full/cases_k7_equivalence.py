"""Astra K7a exact predecessor equivalence on unchanged live function and own business facts."""
from pathlib import Path
import hashlib, subprocess
import cases_business as b
from cases_stage import admin, check, wrap

PREDECESSOR = 'c7c0b1c^'
SOURCE = 'scripts/cp7-src/planning/history-source.sql'

def cases(cur,today):
    def equivalence():
        admin(cur)
        product=Path(b.transport.__file__).resolve().parents[1]
        old=subprocess.check_output(['git','show',PREDECESSOR+':'+SOURCE],cwd=product,text=True)
        first=old[old.index('create function cp7_planning.history_source_within'):]
        first=first[:first.index('$$;')+3]
        check(first.count('create function')==1,'Exactly one pinned predecessor function')
        cur.execute(first.replace('create function cp7_planning.history_source_within','create function pg_temp.astra_k7_old',1),prepare=False)
        sig='cp7_planning.history_source_within(integer)'
        definition=cur.execute('select pg_get_functiondef(%s::regprocedure)',(sig,)).fetchone()[0]
        rows=[]
        def compare(label):
            admin(cur)
            for bound in (0,1,5000):
                def read(name):
                    return cur.execute("select ("+name+"(%s)-'captured_at')::text",(bound,)).fetchone()[0]
                current=read('cp7_planning.history_source_within')
                prior=read('pg_temp.astra_k7_old')
                repeat=read('cp7_planning.history_source_within')
                check(current==repeat,'Fixture did not change during comparison',phase=label,bound=bound)
                check(current==prior,'K7a complete ordered JSON bytes equal predecessor except capture clock',phase=label,bound=bound,current=current,predecessor=prior)
                rows.append(dict(phase=label,bound=bound,bytes=len(current.encode()),sha256=hashlib.sha256(current.encode()).hexdigest(),status='PASS'))
        compare('installed_baseline')
        f=b.production(cur,today);b.assess(cur,f)
        b.drafts.create(cur,f,b.drafts.payload(f,'13','29.91'));p,v=b.cmd.review(cur,f);b.cmd.command(cur,'POST',p,v)
        b.returns.payments.pay(cur,f,'137.03');f['allocations']=b.returns.read(cur,f)['page']['rows'];p,v=b.returns.payload(cur,f,qty='4',refund='119.64');b.cmd.command(cur,'RETURN',p,v)
        compare('own_73_receipt_41_fg_13_sale_4_return')
        admin(cur)
        check(cur.execute('select pg_get_functiondef(%s::regprocedure)',(sig,)).fetchone()[0]==definition,'Actual product function unchanged throughout')
        return dict(comparisons=rows,predecessor_commit=subprocess.check_output(['git','rev-parse',PREDECESSOR],cwd=product,text=True).strip(),predecessor_file_sha256=hashlib.sha256(old.encode()).hexdigest(),current_definition_sha256=hashlib.sha256(definition.encode()).hexdigest(),excluded=['captured_at'],note='Temporary predecessor function only; actual candidate function unchanged. Bounds 0/1 exercise incomplete source, 5000 actual bounded current source. No claim of 5000 products in this small equivalence fixture.')
    return [wrap('ASF-13-K7A-SOURCE-EQUIVALENCE',equivalence)]

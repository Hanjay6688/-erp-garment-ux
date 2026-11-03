"""Explicit Mandor stage over the actual accepted, immutable Afui assembly.

The owning package supplies its trusted installation transaction. Business
cases use its ordinary local Native connection. This wrapper imports no ERP,
opens no connection, changes no component gate, and runs no case on import.
"""
from pathlib import Path
from hashlib import sha256
import json,subprocess
import admission

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FROZEN=ROOT.parent/'qualified-afui-parent'
USED_ERROR='MANDOR_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
CONTRACT='cp7.mandor-shop-on-accepted-afui.v1'


def require(value,message):
    if not value:raise ValueError(message)


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


class Assembly:
    USED_ERROR=USED_ERROR
    def __init__(self,parent_module,parent_fixture,mandor_module,parent_raw):
        # Actual Root acceptance is checked before inspecting any ERP module.
        self.receipt=admission.parent(parent_raw);self.parent_raw=parent_raw
        expected=FROZEN/'scripts/cp7_accessory_nonpayable'
        require(Path(parent_module.__file__).resolve()==expected/'assembly.py','MANDOR_ASSEMBLY_EXACT_FROZEN_AFUI_MODULE')
        require(Path(parent_fixture.__file__).resolve()==expected/'native_fixture.py','MANDOR_ASSEMBLY_EXACT_FROZEN_DOMAIN_FIXTURE')
        require(Path(mandor_module.__file__).resolve()==ROOT/'scripts/cp7_mandor_shop/composition.py','MANDOR_ASSEMBLY_EXACT_CURRENT_MANDOR_MODULE')
        def git(*args):return subprocess.check_output(['git','-C',str(FROZEN),*args])
        require(git('rev-parse','HEAD').decode().strip()==admission.PARENT_HEAD,'MANDOR_ASSEMBLY_EXACT_FROZEN_PARENT_HEAD')
        require(git('rev-parse','HEAD^{tree}').decode().strip()==admission.PARENT_TREE,'MANDOR_ASSEMBLY_EXACT_FROZEN_PARENT_TREE')
        require(subprocess.run(['git','-C',str(FROZEN),'diff','--quiet','HEAD','--']).returncode==0,'MANDOR_ASSEMBLY_FROZEN_PARENT_WORKTREE_CHANGED')
        self._parent=parent_module;self.fixture=parent_fixture;self.mandor=mandor_module
        self.domain_modules=None
        self.sources()

    def parent(self):return self._parent

    def runtime(self):return self._parent.runtime()

    def sources(self):
        admission.parent(self.parent_raw)
        graph=self._parent.sources()
        require(pin(canonical(graph))==self.receipt['qualified_Afui_good_nonpayable_sources'],'MANDOR_ASSEMBLY_COMPLETE_ACTUALLY_QUALIFIED_AFUI_SOURCE_GRAPH')
        own=self.mandor.sources()
        require(own['actual_final_parent_admission']==admission.PARENT_HEAD,'MANDOR_ASSEMBLY_COMPONENT_ACTUAL_PARENT_NOT_BOUND')
        self.mandor.admission.runtime_admission(self.parent_raw)
        return dict(contract=CONTRACT,parent_root=pin(self.parent_raw),qualified_Afui_sources=pin(canonical(graph)),Mandor_sources=own,
            actual_Native_cases=0,actual_Auth_HTTP_cases=0,actual_browser_cases=0,production_go=False,independent_acceptance=False)

    def install_delta(self,cur,qualified_Afui):
        source=self.sources();self.mandor.trusted_installer(cur)
        require(self.mandor.capture(cur)==qualified_Afui['after'],'MANDOR_ASSEMBLY_EXACT_INSTALLED_AFUI_PARENT_REQUIRED')
        # Verify the original parent catalogue and inspect its natural fixtures
        # BEFORE adding new Mandor objects. Their original verifier is strict.
        self.domain_modules=self.fixture.admitted_modules(cur,qualified_Afui)
        child=self.mandor.install(cur,self.parent_raw)
        require(child['before']==qualified_Afui['after'],'MANDOR_ASSEMBLY_COMPLETE_PARENT_CATALOGUE_LINEAGE')
        state=dict(contract=CONTRACT,sources=source,parent=qualified_Afui,Mandor=child,
            before=child['before'],after=child['after'])
        self.verify(cur,state);return state

    def install(self,cur):return self.install_delta(cur,self._parent.install(cur))

    def verify(self,cur,state):
        require(state.get('contract')==CONTRACT and state['sources']==self.sources(),'MANDOR_ASSEMBLY_SOURCE_OR_CONTRACT_CHANGED')
        require(state['before']==state['parent']['after']==state['Mandor']['before']and state['after']==state['Mandor']['after'],
            'MANDOR_ASSEMBLY_PARENT_OR_CHILD_CATALOGUE_BINDING_CHANGED')
        verified=self.mandor.verify(cur,state['Mandor'])
        return dict(contract=CONTRACT,Mandor=verified,entire_qualified_parent_preserved_by_exact_Mandor_transition=True,
            actual_Auth_HTTP_or_browser_qualification=False,production_go=False,independent_acceptance=False)

    def rollback_delta_preuse(self,cur,state):
        self.verify(cur,state)
        try:value=self.mandor.rollback_preuse(cur,state['Mandor'])
        except ValueError as error:
            if str(error).startswith(USED_ERROR+':'):raise ValueError(USED_ERROR)from error
            raise
        require(value['all22_and_Native_raw_authority_restored']is True and value['used_rows_removed']is False,
            'MANDOR_ASSEMBLY_EXACT_UNUSED_NARROW_INVERSE_REQUIRED')
        require(self.mandor.capture(cur)==state['parent']['after'],'MANDOR_ASSEMBLY_UNUSED_INVERSE_MUST_RESTORE_EXACT_AFUI_PARENT')
        return dict(status='MANDOR_EXACT_UNUSED_DELTA_INVERSE',used_guard_before_DDL=True,Mandor=value,
            actual_business_or_used_restore_credit=False,production_go=False,independent_acceptance=False)

    def rollback_preuse(self,cur,state):
        child=self.rollback_delta_preuse(cur,state)
        parent=self._parent.rollback_preuse(cur,state['parent'])
        return dict(status='MANDOR_AND_AFUI_EXACT_UNUSED_INVERSE',Mandor=child,Afui=parent,
            used_guard_before_DDL=True,production_go=False,independent_acceptance=False)


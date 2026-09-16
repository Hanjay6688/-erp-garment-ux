import hashlib,os,subprocess
from pathlib import Path
frozen='1bdca3766f7c9800d68295ff5122798060b8a05d'
allowed={'.github/workflows/cp6-ac-independent-audit.yml',
         'scripts/cp6_ac_independent_audit.py',
         'scripts/cp6_ac_audit_bootstrap.py',
         'docs/cp6-efficient-audit-rule.md',
         '.github/workflows/cp6-full-schema-validation.yml'}
ad_pins={'.github/workflows/cp6-ac-independent-audit.yml': '4fb2d7655fedf1a78cb5a93b85378503292d3aaa821224618bca1221333d7380', 'docs/cp6-ad-competition-handoff.md': 'a49ea97343546a60af656ddc5b4712b4d6cede747b5d37e20237e66d11333254', 'docs/cp6-efficient-audit-rule.md': 'dfa295dec9c1ecbf232de15b708680d9cb7aae3137fb338ab832d71e9f467cbd', 'docs/evidence/cp6-ad-family-disposition.json': '433dfb69ee497f6e65aa71542ac578099044af6f329a7a90617260531d97f822', 'docs/evidence/cp6-ad-predecessor-functions.json': '0a0edbcfd0c4cd26212a161a84f3b7414ecc15fe5642409c868f1f17a0694446', 'docs/evidence/cp6-ad-runtime-pins.json': '077e0dfde7c56ce9b37add1c18683ce8cf6ae8a3433adf29e8c2320cd8a6bd18', 'scripts/cp6_ac_audit_bootstrap.py': '2fccc292f90ae7dc82aeaf7415e0de1d206f69ff47d6228f265aed962a42f466', 'scripts/cp6_ac_independent_audit.py': '2cecb301e0c7323251fa6ff3c707ca57520f2430ca9b571fe6afd223435c9371', 'scripts/cp6_preuse_rollback_maintenance.py': '0e8f30f90d2048ac64d6fa969e86639d1b59732ed170de453d6d3869a421343a', 'scripts/cp6_v2620ad_build_sql.py': '82b8bdb281e609ea8617e710c6f96b899f7fb9d802d6355b9ce42e23dae66d2c', 'scripts/cp6_v2620ad_family_proof.py': '5741fc4a2685e97598c7b9394f1cc2891cc495cfda06d885efb5f3c29611ce5b', 'scripts/cp6_v2620ad_maintenance_schedules.py': '639dd11d8170f11889ee05dd27ee8d69956ee95ec49cd0bd8ed9f7aaf404e179', 'scripts/cp6_v2620ad_proof.py': '29e381b38afc97905d5a60be137fb72835c36cfc186842bd52a766a4855ebd95', 'scripts/cp6_v2620ad_reuse_matrix.py': '7c3e7556d0a8b86010d81d9dcd7eb9a89159379b6b7cdc700bef300d9fb55c1b', 'scripts/cp6_v2620ad_rollback_guards.py': '8a6a9765bb753525f083df9af63a2f8c1b000d3b520f5317b281752a12de953b', 'scripts/cp6_v2620ad_runtime.py': 'c50b59dafa74e6d3edc553569c6360e4573b86d40cc9f4049028b398455ddc57', 'scripts/cp6_v2620h_maintenance_rollback_matrix.py': '5c2a4088c9ed00529d6055380897de0bfff22cbe0d8e359832bff27010012467', 'supabase/migrations/20260915113627_erp_v2_6_20ad_cp6_opening_material_business_day.sql': 'cd4879eb9b053e3b7a975e1430f481131e377f260ece2f19f07bfb4c98498c1d', 'supabase/rollbacks/20260915113627_erp_v2_6_20ad_cp6_opening_material_business_day.rollback.sql': '38eb8025f07fa9a49f221fa274e56242c5c525947c3d24dc98a735d02b75512c'}
round_pins={'.github/workflows/cp6-ad-roll-opening-check.yml': '77bf6c3abcf314a150616419a82faa1b97c99f2c359d6129d10ec35dd2e3efd9',
            'scripts/cp6_ad_roll_opening_check.py': 'fb11a8f87eef368cedc161924950c2f388ba5dd45067618eca435a71c2e70d37'}
ae_pins={**ad_pins,**round_pins}
ae_pins.update({
    '.github/workflows/cp6-ad-roll-opening-check.yml': '09f87131e8954a886593744b24421f713da06c46fc94b435c25e9703c6bd1b22',
    'docs/evidence/cp6-ae-runtime-pins.json': '6891b006b3611debc87a0bc4928438c6db5dc1df8209d9c7d927f151494026d4',
    'scripts/cp6_preuse_rollback_maintenance.py': 'a6f9403c32a6f2a434dccab7bad77c63e6a35a7f2ee4fccb68f810d9b15dd6bd',
    'scripts/cp6_v2620ae_build_sql.py': 'd36adaf08324e25f665ebe6fcf952518a1f33eb08195260bd1c88dbd347c4922',
    'scripts/cp6_v2620ae_family.py': '855f0481b093271412ba291261cad2a8800e75a4a813ef53ba36d94d46dfacd9',
    'scripts/cp6_v2620ae_rollback_guards.py': '434e4d05d3bac0e3d1070f9703f5812c01baf00e61172e92c66b5e420e35229d',
    'scripts/cp6_v2620ae_runtime.py': '6ffccbed42083e1dad2cdc90559cb27e66cb2ee7f54b5519fba85d0fcadfbe33',
    'supabase/migrations/20260915201500_erp_v2_6_20ae_cp6_opening_roll_integrity.sql': '228d9185501d418835e6434e64e1445be7b12ce2f517778ea63d789d478461c1',
    'supabase/rollbacks/20260915201500_erp_v2_6_20ae_cp6_opening_roll_integrity.rollback.sql': 'a869de31481cac1c8a26de17e3be9d47d2b42c18a6756df5cabfc016ebfa0341',
    '.github/workflows/cp6-ac-independent-audit.yml': '464e0b2a85d88ef6cc03373c5999aa9126a646c844a3d28ede075477888eac46',
    'scripts/cp6_v2620ae_maintenance_schedules.py': '7d88f6a54c35c0ae32e25cae4540056945e083603766cdb2ecaa1080582f722d'})
ad_exact=False
ad_round=False
ae_exact=False
ae_independent=False
# BEGIN AI INDEPENDENT ROUTE
ai_independent=False
if Path('scripts/cp6_ai_review_scope.py').exists():
    ai_independent=subprocess.run(['python','scripts/cp6_ai_review_scope.py'],capture_output=True).returncode==0
# END AI INDEPENDENT ROUTE
# BEGIN AI QUALIFIED ROUTE
ai_review=False
if Path('scripts/cp6_ai_gate_scope.py').exists():
    ai_review=subprocess.run(['python','scripts/cp6_ai_gate_scope.py'],capture_output=True).returncode==0
# END AI QUALIFIED ROUTE
# BEGIN AH INDEPENDENT ROUTE
ah_independent=False
if Path('scripts/cp6_ah_review_scope.py').exists():
    ah_independent=subprocess.run(['python','scripts/cp6_ah_review_scope.py'],capture_output=True).returncode==0
# END AH INDEPENDENT ROUTE
# BEGIN AH QUALIFIED ROUTE
ah_review=False
if Path('scripts/cp6_ah_gate_scope.py').exists():
    ah_review=subprocess.run(['python','scripts/cp6_ah_gate_scope.py'],capture_output=True).returncode==0
# END AH QUALIFIED ROUTE
# BEGIN AG RESIDUAL ROUTE
ag_residual=False
if Path('scripts/cp6_ag_residual_scope.py').exists():
    ag_residual=subprocess.run(['python','scripts/cp6_ag_residual_scope.py'],capture_output=True).returncode==0
# END AG RESIDUAL ROUTE
# BEGIN AG QUALIFIED ROUTE
ag_review=False
if Path('scripts/cp6_ag_gate_scope.py').exists():
    ag_review=subprocess.run(['python','scripts/cp6_ag_gate_scope.py'],capture_output=True).returncode==0
# END AG QUALIFIED ROUTE
# BEGIN AF INDEPENDENT ROUTE
af_review=False
if Path('scripts/cp6_af_review_scope.py').exists():
    af_review=subprocess.run(['python','scripts/cp6_af_review_scope.py'],capture_output=True).returncode==0
# END AF INDEPENDENT ROUTE
af_exact=False
af_pins={'.github/workflows/cp6-ad-roll-opening-check.yml': 'a267909274c68a9b41bc250bcd713f3e38de967e65d067cf150f10af55b1afc8', 'docs/cp6-af-competition-handoff.md': '21e5d34d547f26bd3ad2105c3861bfc77e547a9a557d77925212c1245b9dbdc8', 'docs/evidence/cp6-af-family-disposition.json': 'fe17694cb5b2b8cc4924fdd2bcba4eee33788b446c5e173053d30239fa304d70', 'docs/evidence/cp6-af-predecessor-functions.json': '9eafb434cf36de84b40614f031d8f56aa732720aae985cfb092cc5a37319db65', 'docs/evidence/cp6-af-runtime-pins.json': '37ad48da077eb21e40bd9bd125de64e01f46c2a4c10978f3d8f150bb17194453', 'scripts/cp6_preuse_rollback_maintenance.py': '8e13322d92178bb49f151619c0973bdf6108d281e7c47bf25a7eca20b8ceb406', 'scripts/cp6_v2620af_build_sql.py': '3dc4e98889c4669c84b57aa82fd6b6df9da8323949577619d7af02b90c421753', 'scripts/cp6_v2620af_concurrency.py': '83a2b8f5d5b78020476d7c13dd2da0becff93960b988f816c996750a20dfdcbf', 'scripts/cp6_v2620af_family.py': 'bb416174fc5b824c7e0673a1309d37c310344fd25a3c81847a364ae0cf7280d5', 'scripts/cp6_v2620af_maintenance_schedules.py': '72c51a1197a3aa70e54c33d1abadadbf711643524a189d5562ee69b29267bba3', 'scripts/cp6_v2620af_rollback_guards.py': '3f98c9ed99a09e363fe94078ebbabba0c206b5b042d03b9c8fc9bc34f841d9ea', 'scripts/cp6_v2620af_runtime.py': 'a9c0bf0771ad2daaee4715e25ed1f0374bdbe4edd0bafda01d4d83dc2945f8a0', 'supabase/migrations/20260916014332_erp_v2_6_20af_cp6_posted_child_integrity.sql': '54c5f73b99a2e63c858a777f669432f28260177daf4c45d806bb0e8a7c7c8e8e', 'supabase/rollbacks/20260916014332_erp_v2_6_20af_cp6_posted_child_integrity.rollback.sql': 'd417b2ccb0e2cc5cd836e6a3d58ea9f50f2391cd386b31320d82fef7dc542575', '.github/workflows/cp6-ac-independent-audit.yml': 'e4b9997c891e4a32b72d0ae01884cf827f80b5924c707ae975fb7a0204d384ed'}
ae_independent_pins={'.github/workflows/cp6-ad-roll-opening-check.yml': '3028654b84498833c95ddfadd797d6cd23f624c0383cdaacb5f65ee4c0e851d2', 'scripts/cp6_ae_independent_audit.py': 'c73acb420aceeb9cf7dda100af2b5b12095b8022a042fa4b80de5d4ddb157ba4'}
try:
    ancestor=subprocess.check_output(['git','merge-base',frozen,'HEAD'],text=True).strip()==frozen
    changed=set(subprocess.check_output(['git','diff','--name-only',frozen,'HEAD'],text=True).splitlines())
    current=Path('.github/workflows/cp6-full-schema-validation.yml').read_text()
    marker_a='  # BEGIN AC AUDIT EVIDENCE ROUTER\n'
    marker_b='  # END AC AUDIT EVIDENCE ROUTER\n'
    start=current.index(marker_a);end=current.index(marker_b,start)+len(marker_b)
    restored=current[:start]+current[end:]
    routing="    needs: audit-scope\n    if: needs.audit-scope.outputs.full == 'true'\n"
    assert restored.count(routing)==1
    restored=restored.replace(routing,'',1)
    original_matches=hashlib.sha256(restored.encode()).hexdigest()=='5ba14137aca8992f92f32357d2b0a3c15a1ca40a988b3ec79754dde7a6eb8302'
    audit_only=ancestor and bool(changed) and changed<=allowed and original_matches
    ad_exact=(ancestor and original_matches and changed==set(ad_pins)|{str(Path('.github/workflows/cp6-full-schema-validation.yml'))}
        and all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest for path,digest in ad_pins.items()))
    ad_round=(ancestor and original_matches
        and changed==set(ad_pins)|set(round_pins)|{str(Path('.github/workflows/cp6-full-schema-validation.yml'))}
        and all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest for path,digest in ad_pins.items())
        and all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest for path,digest in round_pins.items()))
    ae_exact=(ancestor and original_matches
        and changed==set(ae_pins)|{str(Path('.github/workflows/cp6-full-schema-validation.yml'))}
        and all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest for path,digest in ae_pins.items()))
    ae_independent_head='ce8e8ea5cdfab4b39ea7095c1b3bd1c8ab1f33d1'
    ae_independent_changed=set(subprocess.check_output(['git','diff','--name-only',ae_independent_head,'HEAD'],text=True).splitlines())
    ae_independent=(original_matches
        and subprocess.check_output(['git','merge-base',ae_independent_head,'HEAD'],text=True).strip()==ae_independent_head
        and ae_independent_changed==set(ae_independent_pins)|{'.github/workflows/cp6-full-schema-validation.yml'}
        and all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest for path,digest in ae_independent_pins.items()))
    af_base='fd904a17f88e52104e6ba89874f16bfb654245d6'
    af_changed=set(subprocess.check_output(['git','diff','--name-only',af_base,'HEAD'],text=True).splitlines())
    af_exact=(original_matches
        and subprocess.check_output(['git','merge-base',af_base,'HEAD'],text=True).strip()==af_base
        and af_changed==set(af_pins)|{'.github/workflows/cp6-full-schema-validation.yml'}
        and all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest for path,digest in af_pins.items()))
    reuse=audit_only or ad_exact or ad_round or ae_exact or ae_independent or af_exact or af_review or ag_review or ag_residual or ah_review or ah_independent or ai_review or ai_independent
except (AssertionError,ValueError,OSError,subprocess.CalledProcessError):
    reuse=False
with open(os.environ['GITHUB_OUTPUT'],'a') as output:
    output.write('full='+('false' if reuse else 'true')+'\n')
print('RERUN_REQUIRED: exact AF delta requires its dedicated focused, combined134 and concurrency gate; independent review pending' if af_exact else 'REUSED_EVIDENCE: exact AE business/runtime; separate independent review required' if ae_independent else 'RERUN_REQUIRED: AE combined 134-case business gate and 20 fresh schedules; historical AC evidence retained' if ae_exact else 'REUSED_EVIDENCE: pinned AD plus focused roll-opening round' if ad_round else 'REUSED_EVIDENCE: Native200/AB189 base; pinned AD delta requires the separate whole-family native gate' if ad_exact else 'REUSED_EVIDENCE: exact AC business source' if reuse else 'RERUN_REQUIRED: change outside the pinned audit/AD boundary')

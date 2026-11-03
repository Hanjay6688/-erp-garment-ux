"""Three closed routes in the complete original package; no ERP imports."""
from hashlib import sha256

ORIGINAL='scripts/current-vendor-receivable-qualification/probe.py'
PIN=dict(bytes=12667,sha256='c420d894f8d5f16bddefeae73addb621507170f372a28e7d6e33d88c7eeb0be9')
REPLACEMENTS=(
    ("prior=measured(timings,'SINGLE_FULL_READONLY_PARENT_INSTALL',readonly.install,cur)\n"
     "                prior=measured(timings,'EXACT_BACKEND3194_PARENT_INSTALL',product.parent().install_delta,cur,prior)",
     "prior=measured(timings,'ACTUAL_ACCEPTED_MANDOR17_PARENT_INSTALL',product.parent().install,cur)"),
    ("with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:\n"
     "            try:\n                report['install_boundary_lock']",
     "with trusted_installer_connection()as conn,conn.cursor()as cur:\n"
     "            try:\n                report['install_boundary_lock']"),
    ("report['actual_two_session_races']=3\n"
     "            report['actual_Native_cases']=7\n"
     "            report['actual_Auth_HTTP_cases']=1\n"
     "            report['actual_browser_cases']=0\n"
     "            report['actual_business_cases']=11\n"
     "            report['real_Auth_HTTP_qualified']=True",
     "report['actual_two_session_races']=0\n"
     "            report['actual_Native_cases']=cases[runner.CASE]['actual_Native_cases']\n"
     "            report['actual_Auth_HTTP_cases']=0\n"
     "            report['actual_browser_cases']=0\n"
     "            report['actual_business_cases']=cases[runner.CASE]['actual_Native_cases']\n"
     "            report['real_Auth_HTTP_qualified']=False\n"
     "            report['qualification_scope']='CURRENT_PARENT_SKU_NATIVE6_ONLY'"),
)


def derive(raw):
    if dict(bytes=len(raw),sha256=sha256(raw).hexdigest())!=PIN:
        raise ValueError('SKU_COMPOSITE_EXACT_WHOLE_PACKAGE_ORIGINAL')
    text=raw.decode()
    for before,after in REPLACEMENTS:
        if text.count(before)!=1 or after in text:raise ValueError('SKU_COMPOSITE_EXACT_PACKAGE_ROUTE')
        text=text.replace(before,after,1)
    restored=text
    for before,after in reversed(REPLACEMENTS):
        if restored.count(after)!=1:raise ValueError('SKU_COMPOSITE_EXACT_PACKAGE_INVERSE_ROUTE')
        restored=restored.replace(after,before,1)
    if restored.encode()!=raw:raise ValueError('SKU_COMPOSITE_COMPLETE_PACKAGE_NOT_RECOVERED')
    compile(text,'sku_current_parent_whole_package','exec')
    return text,dict(original=PIN,derived_sha256=sha256(text.encode()).hexdigest(),exact_routes=3,
        complete_original_recovered=True,only_install_transaction_uses_trusted_maintenance=True,
        full_restore_all22_rows_sequences_roles_public_and_advisors_unchanged=True,
        previous_parent_cases_not_counted_as_fresh=True,actual_composite_cases=0,production_go=False)

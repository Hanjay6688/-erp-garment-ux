"""Cold browser source prerequisites; does not start Auth, UI or a database."""
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import ast,json,subprocess
import access_cases

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
IDS=(
 'MANDOR_BROWSER_DESKTOP_NORMAL_PAYROLL_LOST_REPLY_SAME_UUID_TWO_TABS_RELEASE',
 'MANDOR_BROWSER_MOBILE390_NORMAL_PAYROLL_STALE_INPUT_FRESH_READ_RELEASE',
)


def require(value,message):
    if not value:raise ValueError(message)


def check():
    browser=(HERE/'browser.mjs').read_text()
    for name in IDS:require(browser.count(name)==1,'MANDOR_BROWSER_EXACT_TWO_IDS')
    subprocess.run(['node','--check',str(HERE/'browser.mjs')],check=True,capture_output=True)
    for name in('browser_observer.py','browser_preflight.py','browser_gate.py'):
        compile((HERE/name).read_bytes(),str(HERE/name),'exec')
    # A new observer process has no installer-owned legacy control.STATE.
    # Only SQL races may use the original Native schema-overlay context.
    calls=[]
    def legacy(cur):calls.append(cur);raise ValueError('ORIGINAL_NATIVE_OVERLAY_CONTEXT_REQUIRED')
    ctx=access_cases.Context.__new__(access_cases.Context)
    ctx.modules=SimpleNamespace(control=SimpleNamespace(STATE=None,product_catalog=legacy))
    for mode in('HTTP','BROWSER'):
        ctx.mode=mode
        with ctx.catalog_scope(None):pass
        for operation,args in((ctx.read,(None,)),(ctx.allocation,(None,{},'unused')),(ctx.sale_replay,(None,))):
            try:operation(*args)
            except ValueError as error:require(str(error)=='MANDOR_ACCESS_ADMINISTRATIVE_SESSION_IS_NOT_REAL_AUTH',
                'MANDOR_BROWSER_EXPECTED_REAL_AUTH_BOUNDARY')
            else:raise ValueError('MANDOR_BROWSER_SQL_IDENTITY_WAS_MISLABELLED_AUTH')
    require(calls==[],'MANDOR_BROWSER_CANNOT_DEPEND_ON_INSTALLER_PROCESS_STATE')
    ctx.mode='RACE'
    try:
        with ctx.catalog_scope(None):pass
    except ValueError as error:require(str(error)=='ORIGINAL_NATIVE_OVERLAY_CONTEXT_REQUIRED','MANDOR_BROWSER_RACE_ORIGINAL_CONTEXT')
    else:raise ValueError('MANDOR_BROWSER_RACE_OVERLAY_CHECK_WAS_DROPPED')
    require(len(calls)==1,'MANDOR_BROWSER_RACE_CONTEXT_STILL_REQUIRED')
    # These selectors are from the actual current components, not a mock page.
    selectors={
      'src/ConnectedPayrollPage.tsx':['Payroll & Kasbon','Cari payroll','cproc-receipt'],
      'src/MandorShopPayrollPanel.tsx':['Tagihan belanja mandor','Periksa status pemasangan tagihan'],
      'src/MandorShopCards.tsx':['Pasang tagihan belanja','Nominal potongan belanja','Tutup kartu tagihan',
        'Muat ulang tagihan','Pasang tagihan ke payroll','Lepas tagihan dari payroll','Batal memilih tagihan',
        'Saya sudah memeriksa nota, nominal, mandor, dan minggu payroll.'],
    }
    pins={}
    for name,labels in selectors.items():
        raw=(ROOT/name).read_bytes()
        require(all(label in raw.decode()and label in browser for label in labels),'MANDOR_BROWSER_CURRENT_SEMANTIC_UI_SOURCE:'+name)
        pins[name]=dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
    require("await other.getByRole('button',{name:'Tutup kartu tagihan',exact:true}).click()"in browser,
        'MANDOR_BROWSER_NATIVE_MODAL_CLOSED_BEFORE_PARENT_RECOVERY')
    observer=ast.parse((HERE/'browser_observer.py').read_bytes())
    require(not any(isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr in('commit','allocation','sale_replay')
        for n in ast.walk(observer)),'MANDOR_BROWSER_OBSERVER_CANNOT_MUTATE_TRANSACTIONS')
    return dict(status='MANDOR_BROWSER2_SOURCE_PREPARED_NOT_EXECUTED',case_ids=list(IDS),current_UI_pins=pins,
        cold_process_legacy_STATE_required=False,administrative_session_fake_Auth_refusals=6,
        original_race_schema_context_preserved=True,observer_read_only=True,
        actual_browser_cases=0,actual_Auth_HTTP_cases=0,actual_SQL_executed=0,
        production_go=False,independent_acceptance=False)

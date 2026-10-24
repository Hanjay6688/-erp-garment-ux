"""Pure byte admission for exactly two additive Master navigation callbacks."""
from hashlib import sha256

OLD_APP_SHA256='0bca1e95f69c51d3fb394028b41d9df1d5829858c185f0df008202dbaf1c08c4'
MASTER_CALLBACKS=(
 ('<ConnectedFgStockPage purpose="CARD"/>',"<ConnectedFgStockPage purpose=\"CARD\" onOpenMaster={()=>setPage('master-products')}/>"),
 ('<ConnectedFgStockPage/>',"<ConnectedFgStockPage onOpenMaster={()=>setPage('master-products')}/>"),
)


def admit_master_navigation(raw,declared):
    if declared!=OLD_APP_SHA256:raise ValueError('AB_UI_ORIGINAL_APP_PIN_CHANGED')
    text=raw.decode('utf-8')
    for old,new in MASTER_CALLBACKS:
        if text.count(new)!=1 or old in text:raise ValueError('AB_UI_MASTER_CALLBACK_COUNT_CHANGED')
        text=text.replace(new,old,1)
    if sha256(text.encode('utf-8')).hexdigest()!=declared:
        raise ValueError('AB_UI_UNDECLARED_APP_CHANGE')
    return dict(path='src/App.tsx',qualified_original_sha256=declared,
        current_sha256=sha256(raw).hexdigest(),counted_additive_callbacks=2,
        unchanged_other_App_bytes=True,historical_Original_relabelled=False)


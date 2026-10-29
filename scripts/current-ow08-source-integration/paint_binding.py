"""Two source-declared CSS appends; historical money proof stays on its source."""
from hashlib import sha256

APPENDS={
 'src/initial-import.css':'\n/* Unknown-price actions remain legible while disabled; pricing still requires explicit review. */\n.initial-import [aria-label="Cuci gagal harga belum diketahui"] button:disabled { opacity: 1; border-style: dashed; }\n',
 'src/connected-laundry-qc.css':'\n/* A blocked QC inverse remains readable without enabling the authoritative action. */\n.clq-history [data-qc-inspection-id] .clq-reversal button:disabled { opacity: 1; border-style: dashed; }\n',
}

def verify(overlays,changed_product,base_read,current_read):
    assert set(changed_product)==set(APPENDS),'UNDECLARED_OW08_PRODUCT_CHANGE'
    assert len(overlays)==len(APPENDS)and {row['path']for row in overlays}==set(APPENDS),'OW08_PAINT_OVERLAY_SET_CHANGED'
    originals={}
    for row in overlays:
        name=row['path'];before=base_read(name);after=current_read(name)
        assert row['exact_append']==APPENDS[name],'OW08_OTHER_CSS_APPEND_REFUSED'
        assert sha256(before).hexdigest()==row['before_sha256'],'OW08_PAINT_BASE_CHANGED'
        assert after==before+APPENDS[name].encode(),'OW08_PAINT_NOT_EXACT_APPEND'
        assert sha256(after).hexdigest()==row['after_sha256'],'OW08_PAINT_CURRENT_CHANGED'
        originals[name]=before
    return originals

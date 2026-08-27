const qcActiveKey = 'erp.prototypePage'
const qcPageId = 'qc-final-sku'

type QcProduct = {
  brand: string
  sku: string
  name: string
  color: string
  range: string
  sizes: [string, string, string]
  warehouse: string
}

type QcJob = {
  ref: string
  mandor: string
  laundry: string
  productKey: string
  sizes: [string, string, string]
  cut: [number, number, number]
  bs: [number, number, number]
  rewash: [number, number, number]
  stuck: [number, number, number]
}

const qcProducts: QcProduct[] = [
  { brand: 'Vivo', sku: '73001', name: 'Vivo Classic', color: 'Indigo', range: '28–30', sizes: ['28','29','30'], warehouse: 'Gudang FG Utama' },
  { brand: 'Vivo', sku: '73002', name: 'Vivo Regular', color: 'Washed Blue', range: '31–33', sizes: ['31','32','33'], warehouse: 'Gudang FG Utama' },
  { brand: 'Vivo', sku: '73003', name: 'Vivo Relaxed', color: 'Charcoal', range: '34–36', sizes: ['34','35','36'], warehouse: 'Gudang FG Utama' },
  { brand: 'Widie', sku: '73001', name: 'Widie Daily', color: 'Dark Navy', range: '28–30', sizes: ['28','29','30'], warehouse: 'Gudang FG Utama' },
  { brand: 'Widie', sku: '73002', name: 'Widie Regular', color: 'Vintage Blue', range: '31–33', sizes: ['31','32','33'], warehouse: 'Gudang FG Cadangan' },
]

const qcJobs: QcJob[] = [
  { ref: 'PO-260827-042', mandor: 'Mandor Afat', laundry: 'Laundry Sumber Warna', productKey: 'Vivo::73002', sizes: ['31','32','33'], cut: [229,225,222], bs: [2,1,1], rewash: [1,0,1], stuck: [0,1,0] },
  { ref: 'PO-260812-031', mandor: 'Mandor Asep', laundry: 'Laundry Sumber Warna', productKey: 'Vivo::73002', sizes: ['31','32','33'], cut: [28,28,28], bs: [1,0,1], rewash: [0,1,0], stuck: [1,0,0] },
  { ref: 'PO-260815-033', mandor: 'Mandor Asep', laundry: 'Laundry Biru Jaya', productKey: 'Vivo::73001', sizes: ['28','29','30'], cut: [24,24,24], bs: [0,1,0], rewash: [1,0,0], stuck: [0,0,0] },
  { ref: 'PO-260812-028', mandor: 'Mandor Dedi', laundry: 'Laundry Biru Jaya', productKey: 'Vivo::73001', sizes: ['28','29','30'], cut: [24,24,24], bs: [0,1,0], rewash: [1,0,0], stuck: [0,0,1] },
  { ref: 'PO-260811-024', mandor: 'Mandor Rudi', laundry: 'Laundry Sumber Warna', productKey: 'Widie::73001', sizes: ['28','29','30'], cut: [16,16,16], bs: [1,0,0], rewash: [0,0,0], stuck: [0,1,0] },
]

function qcProductKey(product: QcProduct) { return `${product.brand}::${product.sku}` }
function qcLocalDateTimeValue(date = new Date()) { const offsetMs = date.getTimezoneOffset() * 60_000; return new Date(date.getTime() - offsetMs).toISOString().slice(0,16) }
function qcDozenPieces(pcs: number) { return `${Math.floor(Math.max(0, pcs) / 12)} lusin · ${Math.max(0, pcs) % 12} potong` }
function qcInt(value: string | number) { const parsed = Number(value); return Number.isFinite(parsed) ? Math.max(0, Math.round(parsed)) : 0 }
function qcJobTotal(job: QcJob) { return job.cut.reduce((sum,qty)=>sum+qty,0) }
const qcMandors = Array.from(new Set(qcJobs.map((job)=>job.mandor)))
function qcJobOptions(mandor: string, selectedRef?: string) {
  return qcJobs.map((job,index)=>({job,index})).filter(({job})=>job.mandor===mandor).map(({job,index})=>`<option value="${index}" ${job.ref===selectedRef?'selected':''}>${job.ref} · ${qcJobTotal(job)} pcs · ${qcDozenPieces(qcJobTotal(job))}</option>`).join('')
}

function qcSetTopTitle(active: boolean) {
  const topTitle = document.querySelector<HTMLElement>('.top-title')
  const strong = topTitle?.querySelector<HTMLElement>('strong')
  const sub = topTitle?.querySelector<HTMLElement>('span')
  if (!strong || !sub) return
  if (active) { strong.textContent = 'QC & Final SKU'; sub.textContent = 'Finishing, pengecualian, dan Barang Jadi' }
  else { strong.textContent = 'Modul ERP'; sub.textContent = 'Cepat, jelas, dan aman buat operasional' }
}

function qcGenericPlaceholder(root: HTMLElement) {
  root.className = 'panel placeholder'
  root.removeAttribute('data-qc-ready')
  root.innerHTML = '<div class="placeholder-icon">◇</div><h2>Fondasinya sudah disiapkan.</h2><p>Modul ini berikutnya akan mengikuti flow bisnis yang sama: informasi penting terlihat sebelum user menekan tombol yang mengubah uang atau stok.</p>'
}
function qcUnmount() { const root = document.querySelector<HTMLElement>('.qc-prototype-root'); if (root) qcGenericPlaceholder(root); qcCloseReview(); qcSetTopTitle(false) }

function qcCurrentJob(root: HTMLElement) { return qcJobs[Number(root.querySelector<HTMLSelectElement>('[data-qc-job]')?.value ?? 0)] ?? qcJobs[0] }
function qcCurrentProduct(root: HTMLElement) {
  const brand = root.querySelector<HTMLSelectElement>('[data-qc-brand]')?.value ?? 'Vivo'
  const sku = root.querySelector<HTMLSelectElement>('[data-qc-sku]')?.value ?? '73002'
  return qcProducts.find((p) => p.brand === brand && p.sku === sku) ?? qcProducts[0]
}
function qcSetText(root: HTMLElement | Document, selector: string, text: string) { const node = root.querySelector<HTMLElement>(selector); if (node) node.textContent = text }
function qcProductOptions(brand: string, selected?: string) { return qcProducts.filter((p) => p.brand === brand).map((p) => `<option value="${p.sku}" ${p.sku === selected ? 'selected' : ''}>${p.sku} · ${p.name}</option>`).join('') }

function qcSizeRow(job: QcJob, index: number) {
  const size = job.sizes[index]
  return `<section class="qc-size-column qc-finish-row" data-qc-size-index="${index}">
    <div class="qc-size-head"><span>SIZE</span><strong>${size}</strong></div>
    <div class="qc-source-cut"><span>POTONGAN</span><strong data-qc-cut>${job.cut[index]} pcs</strong><small>${qcDozenPieces(job.cut[index])}</small></div>
    <label class="qc-grade bs"><span>BS <small>→ Barang BS</small></span><input data-grade="bs" type="number" min="0" value="${job.bs[index]}" inputmode="numeric"/><em>pilih treatment nanti</em></label>
    <label class="qc-grade rewash"><span>CU · CUCI ULANG <small>→ Rework Laundry</small></span><input data-grade="rewash" type="number" min="0" value="${job.rewash[index]}" inputmode="numeric"/><em>kategori BS, jalur laundry</em></label>
    <label class="qc-grade stuck"><span>STUCK LAUNDRY <small>→ tetap di Laundry</small></span><input data-grade="stuck" type="number" min="0" value="${job.stuck[index]}" inputmode="numeric"/><em>bukan FG dan belum jadi BS fisik</em></label>
    <div class="qc-auto-good"><span>GOOD · OTOMATIS</span><strong data-qc-good-size>0 pcs</strong><small data-qc-good-dozen>0 lusin · 0 potong</small></div>
  </section>`
}

function qcRender(root: HTMLElement) {
  if (root.dataset.qcReady === 'true') return
  root.dataset.qcReady = 'true'; root.className = 'qc-prototype-root'
  const job = qcJobs[0]
  const initialProduct = qcProducts.find((p) => qcProductKey(p) === job.productKey) ?? qcProducts[0]
  const brands = Array.from(new Set(qcProducts.map((p) => p.brand)))
  const physicalAt = sessionStorage.getItem('erp.qcPhysicalAt') || qcLocalDateTimeValue()

  root.innerHTML = `
    <section class="hero-copy compact qc-hero">
      <div class="eyebrow">PRODUKSI · FINISHING · BARANG JADI</div>
      <h1>QC & Final SKU</h1>
      <p>Good tidak diketik ulang. Basisnya jumlah Potongan per size, lalu otomatis berkurang oleh BS, Cuci Ulang, dan Stuck Laundry.</p>
    </section>
    <section class="qc-layout">
      <div class="panel qc-workbench">
        <div class="qc-section qc-source-section">
          <div class="qc-section-title"><div><span>01</span><div><strong>Cari sumber Potongan</strong><small>Pilih mandor dulu supaya daftar PO pendek. Jumlah per size tetap ditarik dari Potongan, bukan diketik ulang.</small></div></div><span class="qc-status-pill">DATA SIMULASI</span></div>
          <div class="qc-source-picker">
            <div class="qc-mandor-first"><span class="qc-pick-step">1</span><label class="field"><span>Mandor</span><select class="qc-select" data-qc-mandor-filter>${qcMandors.map((mandor)=>`<option ${mandor===job.mandor?'selected':''}>${mandor}</option>`).join('')}</select></label><div class="qc-picker-hint"><strong data-qc-po-count>${qcJobs.filter((item)=>item.mandor===job.mandor).length} PO</strong><small>tersedia untuk dipilih</small></div></div>
            <div class="qc-po-second"><span class="qc-pick-step">2</span><div class="qc-source-grid">
              <label class="field"><span>PO / grup produksi</span><select class="qc-select" data-qc-job>${qcJobOptions(job.mandor,job.ref)}</select><small class="qc-select-help">Nomor PO · total Potongan · konversi lusin</small></label>
              <div class="qc-source-fact"><span>POTONGAN</span><strong data-qc-cut-total>${qcJobTotal(job)} pcs</strong><small data-qc-cut-dozen>${qcDozenPieces(qcJobTotal(job))}</small></div>
              <div class="qc-source-fact"><span>LAUNDRY</span><strong data-qc-laundry>${job.laundry}</strong><small data-qc-mandor>${job.mandor}</small></div>
            </div></div>
          </div>
        </div>
        <div class="qc-section">
          <div class="qc-section-title"><div><span>02</span><div><strong>Final SKU & waktu fisik</strong><small>Merek tetap bagian dari identitas SKU. Waktu fisik boleh berbeda dari waktu input.</small></div></div></div>
          <div class="qc-product-grid">
            <label class="field"><span>Merek</span><select class="qc-select" data-qc-brand>${brands.map((brand)=>`<option ${brand===initialProduct.brand?'selected':''}>${brand}</option>`).join('')}</select></label>
            <label class="field"><span>SKU final</span><select class="qc-select" data-qc-sku>${qcProductOptions(initialProduct.brand,initialProduct.sku)}</select></label>
            <label class="field"><span>Tanggal & jam fisik</span><input class="qc-date-input" data-qc-physical type="datetime-local" value="${physicalAt}"/></label>
          </div>
          <div class="qc-product-banner"><div><span class="brand-chip strong" data-qc-product-brand>${initialProduct.brand}</span><strong data-qc-product-sku>${initialProduct.sku}</strong><small data-qc-product-name>${initialProduct.name} · ${initialProduct.color} · Range ${initialProduct.range}</small></div><div><span>GOOD MASUK</span><strong data-qc-warehouse>${initialProduct.warehouse}</strong><small>Mutasi: QC → FG</small></div></div>
        </div>
        <div class="qc-section qc-result-section">
          <div class="qc-section-title"><div><span>03</span><div><strong>Hasil finishing per size</strong><small>Rework tidak dicatat sebagai hasil QC. Rework baru dipilih dari menu Barang BS & Rework.</small></div></div><button class="soft-btn" type="button" data-qc-reset>Reset pengecualian</button></div>
          <div class="qc-size-grid qc-finish-grid" data-qc-size-grid>${[0,1,2].map((i)=>qcSizeRow(job,i)).join('')}</div>
        </div>
        <div class="qc-section qc-note-section"><label class="field"><span>Catatan finishing · opsional</span><textarea data-qc-note placeholder="Contoh: size 31 satu pcs stuck di laundry, size 32 satu pcs cuci ulang"></textarea></label></div>
      </div>
      <aside class="panel qc-review-card">
        <div class="eyebrow">RINGKASAN FINISHING</div><h2>Dari Potongan ke FG</h2>
        <div class="qc-review-metric source"><span>POTONGAN</span><strong data-qc-summary-cut>0 pcs</strong><small>basis otomatis</small></div>
        <div class="qc-review-metric good"><span>GOOD · MASUK FG</span><strong data-qc-good>0 pcs</strong><small data-qc-good-dozen>0 lusin · 0 potong</small></div>
        <div class="qc-review-metric bs"><span>BS · BARANG BS</span><strong data-qc-bs>0 pcs</strong><small>treatment dipilih setelahnya</small></div>
        <div class="qc-review-metric rewash"><span>CU · CUCI ULANG</span><strong data-qc-rewash>0 pcs</strong><small>masuk jalur rework laundry</small></div>
        <div class="qc-review-metric stuck"><span>STUCK LAUNDRY</span><strong data-qc-stuck>0 pcs</strong><small>tetap outstanding di laundry</small></div>
        <div class="qc-check success" data-qc-check><span>✓</span><div><strong>Komposisi konsisten</strong><small>Good dihitung otomatis.</small></div></div>
        <div class="qc-review-context"><span data-qc-review-ref>${job.ref}</span><b>•</b><span data-qc-review-product>${initialProduct.brand} ${initialProduct.sku}</span></div>
        <button class="primary-btn qc-review-button" type="button" data-qc-review>Review finishing <span>→</span></button>
        <small class="qc-prototype-note">Frontend simulasi · tidak menulis stok atau backend.</small>
      </aside>
    </section>
    <div class="qc-review-shield" data-qc-review-shield hidden></div>
    <section class="qc-review-sheet" data-qc-review-sheet hidden>
      <div class="qc-sheet-head"><div><span>REVIEW FINISHING</span><strong data-qc-sheet-title>${initialProduct.brand} · ${initialProduct.sku}</strong></div><button type="button" data-qc-close>×</button></div>
      <div class="qc-sheet-flow"><div class="good"><span>Good → FG</span><strong data-qc-sheet-good>0 pcs</strong></div><div class="bs"><span>BS → Barang BS</span><strong data-qc-sheet-bs>0 pcs</strong></div><div class="rewash"><span>Cuci ulang</span><strong data-qc-sheet-rewash>0 pcs</strong></div><div class="stuck"><span>Stuck Laundry</span><strong data-qc-sheet-stuck>0 pcs</strong></div></div>
      <div class="qc-sheet-audit"><span>Tanggal fisik</span><strong data-qc-sheet-physical>—</strong><small>Good otomatis dari Potongan − BS − Cuci Ulang − Stuck Laundry.</small></div>
      <div class="qc-routing-note"><strong>Sesudah finishing</strong><span>BS baru bisa dipilih treatment-nya di <b>Barang BS & Rework</b>. Bikin bagus ke mandor menghasilkan komponen rework yang eligible payroll; Cuci Ulang menuju laundry.</span></div>
      <div class="qc-sheet-actions"><button class="soft-btn" type="button" data-qc-close>Kembali edit</button><button class="primary-btn" type="button" data-qc-simulate>Simulasikan hasil</button></div>
      <div class="qc-simulation-result" data-qc-simulation hidden><strong>Simulasi alur berhasil.</strong><span>Good akan masuk FG. BS menjadi kasus BS. Cuci Ulang menuju rework laundry. Stuck tetap di Laundry WIP. Backend belum berubah.</span></div>
    </section>`
  qcBind(root); qcRecalculate(root)
}

function qcLoadJob(root: HTMLElement) {
  const job = qcCurrentJob(root)
  const product = qcProducts.find((p)=>qcProductKey(p)===job.productKey) ?? qcProducts[0]
  const mandor = root.querySelector<HTMLSelectElement>('[data-qc-mandor-filter]'); const brand = root.querySelector<HTMLSelectElement>('[data-qc-brand]'); const sku = root.querySelector<HTMLSelectElement>('[data-qc-sku]')
  if (mandor) mandor.value = job.mandor
  if (brand) brand.value = product.brand
  if (sku) { sku.innerHTML = qcProductOptions(product.brand,product.sku); sku.value = product.sku }
  qcSetText(root,'[data-qc-cut-total]',`${qcJobTotal(job)} pcs`); qcSetText(root,'[data-qc-cut-dozen]',qcDozenPieces(qcJobTotal(job)))
  qcSetText(root,'[data-qc-po-count]',`${qcJobs.filter((item)=>item.mandor===job.mandor).length} PO`); qcSetText(root,'[data-qc-mandor]',job.mandor); qcSetText(root,'[data-qc-laundry]',job.laundry); qcSetText(root,'[data-qc-review-ref]',job.ref)
  const grid = root.querySelector<HTMLElement>('[data-qc-size-grid]'); if (grid) grid.innerHTML = [0,1,2].map((i)=>qcSizeRow(job,i)).join('')
  qcUpdateProduct(root); qcRecalculate(root)
}
function qcLoadMandor(root: HTMLElement) {
  const mandor=root.querySelector<HTMLSelectElement>('[data-qc-mandor-filter]')?.value??qcMandors[0]
  const jobSelect=root.querySelector<HTMLSelectElement>('[data-qc-job]')
  const firstIndex=qcJobs.findIndex((job)=>job.mandor===mandor)
  if(jobSelect){jobSelect.innerHTML=qcJobOptions(mandor);jobSelect.value=String(Math.max(0,firstIndex))}
  qcLoadJob(root)
}
function qcUpdateProduct(root: HTMLElement) {
  const product = qcCurrentProduct(root)
  qcSetText(root,'[data-qc-product-brand]',product.brand); qcSetText(root,'[data-qc-product-sku]',product.sku); qcSetText(root,'[data-qc-product-name]',`${product.name} · ${product.color} · Range ${product.range}`); qcSetText(root,'[data-qc-warehouse]',product.warehouse); qcSetText(root,'[data-qc-review-product]',`${product.brand} ${product.sku}`); qcSetText(document,'[data-qc-sheet-title]',`${product.brand} · ${product.sku}`)
}

function qcRecalculate(root: HTMLElement) {
  const job = qcCurrentJob(root); let goodTotal=0,bsTotal=0,rewashTotal=0,stuckTotal=0,invalid=false
  root.querySelectorAll<HTMLElement>('[data-qc-size-index]').forEach((row)=>{
    const index = Number(row.dataset.qcSizeIndex ?? 0), cut = job.cut[index]
    const bs=qcInt(row.querySelector<HTMLInputElement>('[data-grade="bs"]')?.value ?? 0), rewash=qcInt(row.querySelector<HTMLInputElement>('[data-grade="rewash"]')?.value ?? 0), stuck=qcInt(row.querySelector<HTMLInputElement>('[data-grade="stuck"]')?.value ?? 0)
    const exceptions=bs+rewash+stuck; if(exceptions>cut) invalid=true; const good=Math.max(0,cut-exceptions)
    qcSetText(row,'[data-qc-good-size]',`${good} pcs`); qcSetText(row,'[data-qc-good-dozen]',qcDozenPieces(good)); row.classList.toggle('is-invalid',exceptions>cut)
    goodTotal+=good; bsTotal+=bs; rewashTotal+=rewash; stuckTotal+=stuck
  })
  const cutTotal=job.cut.reduce((a,b)=>a+b,0)
  qcSetText(root,'[data-qc-summary-cut]',`${cutTotal} pcs`); qcSetText(root,'[data-qc-good]',`${goodTotal} pcs`); qcSetText(root,'[data-qc-good-dozen]',qcDozenPieces(goodTotal)); qcSetText(root,'[data-qc-bs]',`${bsTotal} pcs`); qcSetText(root,'[data-qc-rewash]',`${rewashTotal} pcs`); qcSetText(root,'[data-qc-stuck]',`${stuckTotal} pcs`)
  qcSetText(document,'[data-qc-sheet-good]',`${goodTotal} pcs`); qcSetText(document,'[data-qc-sheet-bs]',`${bsTotal} pcs`); qcSetText(document,'[data-qc-sheet-rewash]',`${rewashTotal} pcs`); qcSetText(document,'[data-qc-sheet-stuck]',`${stuckTotal} pcs`)
  const check=root.querySelector<HTMLElement>('[data-qc-check]'); const review=root.querySelector<HTMLButtonElement>('[data-qc-review]')
  if(check){check.classList.toggle('success',!invalid);check.classList.toggle('warn',invalid);check.innerHTML=invalid?'<span>!</span><div><strong>Pengecualian melebihi Potongan</strong><small>BS + Cuci Ulang + Stuck tidak boleh lebih besar dari qty Potongan pada size tersebut.</small></div>':`<span>✓</span><div><strong>Good otomatis ${goodTotal} pcs</strong><small>${cutTotal} Potongan − ${bsTotal} BS − ${rewashTotal} CU − ${stuckTotal} Stuck.</small></div>`}
  if(review) review.disabled=invalid
}
function qcOpenReview(root: HTMLElement){const physical=root.querySelector<HTMLInputElement>('[data-qc-physical]')?.value??'';qcSetText(document,'[data-qc-sheet-physical]',physical?physical.replace('T',' · '):'—');const sheet=document.querySelector<HTMLElement>('[data-qc-review-sheet]');const shield=document.querySelector<HTMLElement>('[data-qc-review-shield]');if(sheet)sheet.hidden=false;if(shield)shield.hidden=false;document.body.classList.add('qc-sheet-open')}
function qcCloseReview(){const sheet=document.querySelector<HTMLElement>('[data-qc-review-sheet]');const shield=document.querySelector<HTMLElement>('[data-qc-review-shield]');if(sheet)sheet.hidden=true;if(shield)shield.hidden=true;document.body.classList.remove('qc-sheet-open')}
function qcBind(root: HTMLElement){
  root.addEventListener('input',(event)=>{const target=event.target as HTMLInputElement|null;if(!target)return;if(target.matches('input[data-grade]'))qcRecalculate(root);if(target.matches('[data-qc-physical]'))sessionStorage.setItem('erp.qcPhysicalAt',target.value)})
  root.addEventListener('change',(event)=>{const target=event.target as HTMLSelectElement|null;if(!target)return;if(target.matches('[data-qc-mandor-filter]'))qcLoadMandor(root);else if(target.matches('[data-qc-job]'))qcLoadJob(root);if(target.matches('[data-qc-brand]')){const sku=root.querySelector<HTMLSelectElement>('[data-qc-sku]');if(sku)sku.innerHTML=qcProductOptions(target.value);qcUpdateProduct(root)}if(target.matches('[data-qc-sku]'))qcUpdateProduct(root)})
  root.querySelector<HTMLButtonElement>('[data-qc-reset]')?.addEventListener('click',()=>{root.querySelectorAll<HTMLInputElement>('input[data-grade]').forEach((input)=>input.value='0');qcRecalculate(root)})
  root.querySelector<HTMLButtonElement>('[data-qc-review]')?.addEventListener('click',()=>qcOpenReview(root));document.querySelectorAll<HTMLElement>('[data-qc-close],[data-qc-review-shield]').forEach((node)=>node.addEventListener('click',qcCloseReview));document.querySelector<HTMLButtonElement>('[data-qc-simulate]')?.addEventListener('click',()=>{const result=document.querySelector<HTMLElement>('[data-qc-simulation]');if(result)result.hidden=false})
}
function qcMountIfNeeded(){if(sessionStorage.getItem(qcActiveKey)!==qcPageId)return;const placeholder=document.querySelector<HTMLElement>('.placeholder');if(!placeholder)return;qcSetTopTitle(true);qcRender(placeholder)}
document.addEventListener('click',(event)=>{const target=event.target as Element|null;const submenu=target?.closest('.submenu button') as HTMLButtonElement|null;if(submenu){const label=submenu.textContent?.replace(/^•\s*/,'').trim()??'';if(label==='QC & Final SKU')sessionStorage.setItem(qcActiveKey,qcPageId);else if(sessionStorage.getItem(qcActiveKey)===qcPageId){sessionStorage.removeItem(qcActiveKey);qcUnmount()}}const mainNav=target?.closest('.nav-main');if(mainNav&&!submenu&&sessionStorage.getItem(qcActiveKey)===qcPageId){sessionStorage.removeItem(qcActiveKey);qcUnmount()}},true)
const qcObserver=new MutationObserver(qcMountIfNeeded);qcObserver.observe(document.documentElement,{childList:true,subtree:true});queueMicrotask(qcMountIfNeeded)

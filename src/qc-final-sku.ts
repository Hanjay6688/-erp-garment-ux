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

const qcProducts: QcProduct[] = [
  { brand: 'Vivo', sku: '73001', name: 'Vivo Classic', color: 'Indigo', range: '28–30', sizes: ['28','29','30'], warehouse: 'Gudang FG Utama' },
  { brand: 'Vivo', sku: '73002', name: 'Vivo Regular', color: 'Washed Blue', range: '31–33', sizes: ['31','32','33'], warehouse: 'Gudang FG Utama' },
  { brand: 'Vivo', sku: '73003', name: 'Vivo Relaxed', color: 'Charcoal', range: '34–36', sizes: ['34','35','36'], warehouse: 'Gudang FG Utama' },
  { brand: 'Widie', sku: '73001', name: 'Widie Daily', color: 'Dark Navy', range: '28–30', sizes: ['28','29','30'], warehouse: 'Gudang FG Utama' },
  { brand: 'Widie', sku: '73002', name: 'Widie Regular', color: 'Vintage Blue', range: '31–33', sizes: ['31','32','33'], warehouse: 'Gudang FG Cadangan' },
]

const qcJobs = [
  { ref: 'PO-260812-031', mandor: 'Mandor Asep', source: 'Laundry Selesai', qty: 84 },
  { ref: 'PO-260812-028', mandor: 'Mandor Dedi', source: 'Laundry Selesai', qty: 72 },
  { ref: 'PO-260811-024', mandor: 'Mandor Rudi', source: 'QC tertunda', qty: 48 },
]

function qcLocalDateTimeValue(date = new Date()) {
  const offsetMs = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16)
}

function qcParseQty(value: string) {
  const normalized = value.toLowerCase().replace(',', '.')
  const dozenMatch = normalized.match(/([0-9]+(?:\.[0-9]+)?)\s*(?:lusin|lsn|dozen)/)
  const pcsMatch = normalized.match(/([0-9]+(?:\.[0-9]+)?)\s*(?:pcs|pc|piece|biji|potong|ptg)/)
  if (dozenMatch || pcsMatch) {
    const dozen = dozenMatch ? Number(dozenMatch[1]) * 12 : 0
    const pcs = pcsMatch ? Number(pcsMatch[1]) : 0
    return Math.max(0, Math.round(dozen + pcs))
  }
  const plain = Number(normalized.replace(/[^0-9.]/g, ''))
  return Number.isNaN(plain) ? 0 : Math.max(0, Math.round(plain))
}

function qcDozenPieces(pcs: number) {
  return `${Math.floor(Math.max(0, pcs) / 12)} lusin · ${Math.max(0, pcs) % 12} potong`
}

function qcSetTopTitle(active: boolean) {
  const topTitle = document.querySelector<HTMLElement>('.top-title')
  const strong = topTitle?.querySelector<HTMLElement>('strong')
  const sub = topTitle?.querySelector<HTMLElement>('span')
  if (!strong || !sub) return
  if (active) {
    strong.textContent = 'QC & Final SKU'
    sub.textContent = 'Hasil QC, grade, dan masuk Barang Jadi'
  }
}

function qcGenericPlaceholder(root: HTMLElement) {
  root.className = 'panel placeholder'
  root.removeAttribute('data-qc-ready')
  root.innerHTML = '<div class="placeholder-icon">◇</div><h2>Fondasinya sudah disiapkan.</h2><p>Modul ini berikutnya akan mengikuti flow bisnis yang sama: informasi penting terlihat sebelum user menekan tombol yang mengubah uang atau stok.</p>'
}

function qcUnmount() {
  const root = document.querySelector<HTMLElement>('.qc-prototype-root')
  if (root) qcGenericPlaceholder(root)
}

function qcProductOptions(brand: string, selectedSku?: string) {
  return qcProducts.filter((product) => product.brand === brand).map((product) => `<option value="${product.sku}" ${product.sku === selectedSku ? 'selected' : ''}>${product.sku} · ${product.name}</option>`).join('')
}

function qcSizeColumn(size: string, index: number, defaults: [string,string,string]) {
  const [good, bs, rework] = defaults
  return `<section class="qc-size-column" data-qc-size-index="${index}">
    <div class="qc-size-head"><span>SIZE</span><strong>${size}</strong></div>
    <label class="qc-grade good"><span>GOOD <small>→ masuk FG</small></span><input data-grade="good" value="${good}" inputmode="text" placeholder="0 pcs"/><em data-conversion="good">${qcDozenPieces(qcParseQty(good))}</em></label>
    <label class="qc-grade bs"><span>BS <small>→ barang BS</small></span><input data-grade="bs" value="${bs}" inputmode="text" placeholder="0 pcs"/><em data-conversion="bs">${qcDozenPieces(qcParseQty(bs))}</em></label>
    <label class="qc-grade rework"><span>REWORK <small>→ perbaikan</small></span><input data-grade="rework" value="${rework}" inputmode="text" placeholder="0 pcs"/><em data-conversion="rework">${qcDozenPieces(qcParseQty(rework))}</em></label>
    <div class="qc-size-total"><span>DIPERIKSA</span><strong data-size-total>0 pcs</strong><small data-size-total-dozen>0 lusin · 0 potong</small></div>
  </section>`
}

function qcRender(root: HTMLElement) {
  if (root.dataset.qcReady === 'true') return
  root.dataset.qcReady = 'true'
  root.className = 'qc-prototype-root'
  const initialProduct = qcProducts.find((product) => product.brand === 'Vivo' && product.sku === '73002') ?? qcProducts[0]
  const brands = Array.from(new Set(qcProducts.map((product) => product.brand)))
  const physicalAt = sessionStorage.getItem('erp.qcPhysicalAt') || qcLocalDateTimeValue()

  root.innerHTML = `
    <section class="hero-copy compact qc-hero">
      <div class="eyebrow">PRODUKSI · QC · BARANG JADI</div>
      <h1>QC & Final SKU</h1>
      <p>Catat hasil fisik per size. Good masuk stok FG; BS dan Rework tetap dipisahkan supaya stok tidak tercampur.</p>
    </section>

    <section class="qc-layout">
      <div class="panel qc-workbench">
        <div class="qc-section qc-source-section">
          <div class="qc-section-title"><div><span>01</span><div><strong>Sumber pekerjaan</strong><small>Pilih grup/PO yang benar-benar sedang diperiksa.</small></div></div><span class="qc-status-pill">SIAP QC</span></div>
          <div class="qc-source-grid">
            <label class="field"><span>PO / grup produksi</span><select class="qc-select" data-qc-job>${qcJobs.map((job, index) => `<option value="${index}">${job.ref} · ${job.mandor}</option>`).join('')}</select></label>
            <div class="qc-source-fact"><span>SUMBER</span><strong data-qc-source>${qcJobs[0].source}</strong><small data-qc-job-qty>${qcJobs[0].qty} pcs · ${qcDozenPieces(qcJobs[0].qty)}</small></div>
            <div class="qc-source-fact"><span>MANDOR</span><strong data-qc-mandor>${qcJobs[0].mandor}</strong><small>Jejak produksi tetap ikut PO</small></div>
          </div>
        </div>

        <div class="qc-section">
          <div class="qc-section-title"><div><span>02</span><div><strong>Final SKU & waktu fisik</strong><small>Merek adalah bagian identitas SKU. Tanggal boleh kemarin kalau laporan terlambat.</small></div></div></div>
          <div class="qc-product-grid">
            <label class="field"><span>Merek</span><select class="qc-select" data-qc-brand>${brands.map((brand) => `<option ${brand === initialProduct.brand ? 'selected' : ''}>${brand}</option>`).join('')}</select></label>
            <label class="field"><span>SKU final</span><select class="qc-select" data-qc-sku>${qcProductOptions(initialProduct.brand, initialProduct.sku)}</select></label>
            <label class="field"><span>Tanggal & jam fisik</span><input class="qc-date-input" data-qc-physical type="datetime-local" value="${physicalAt}"/></label>
          </div>
          <div class="qc-product-banner">
            <div><span class="brand-chip strong" data-qc-product-brand>${initialProduct.brand}</span><strong data-qc-product-sku>${initialProduct.sku}</strong><small data-qc-product-name>${initialProduct.name} · ${initialProduct.color} · Range ${initialProduct.range}</small></div>
            <div><span>Tujuan Good</span><strong data-qc-warehouse>${initialProduct.warehouse}</strong><small>Mutasi: QC → FG</small></div>
          </div>
        </div>

        <div class="qc-section qc-result-section">
          <div class="qc-section-title"><div><span>03</span><div><strong>Hasil per size</strong><small>Boleh ketik PCS, lusin, atau campuran. Total dihitung otomatis.</small></div></div><button class="soft-btn" type="button" data-qc-zero>Reset angka</button></div>
          <div class="qc-size-grid" data-qc-size-grid>
            ${qcSizeColumn(initialProduct.sizes[0],0,['24 pcs','2 pcs','1 pcs'])}
            ${qcSizeColumn(initialProduct.sizes[1],1,['24 pcs','1 pcs','2 pcs'])}
            ${qcSizeColumn(initialProduct.sizes[2],2,['24 pcs','0 pcs','1 pcs'])}
          </div>
        </div>

        <div class="qc-section qc-note-section">
          <label class="field"><span>Catatan QC · opsional</span><textarea data-qc-note placeholder="Contoh: 1 pcs size 32 jahitan samping dibuka ulang"></textarea></label>
        </div>
      </div>

      <aside class="panel qc-review-card">
        <div class="eyebrow">RINGKASAN HASIL</div>
        <h2>Ke mana barang bergerak?</h2>
        <div class="qc-review-metric good"><span>GOOD · MASUK FG</span><strong data-qc-good>0 pcs</strong><small data-qc-good-dozen>0 lusin · 0 potong</small></div>
        <div class="qc-review-metric bs"><span>BARANG BS</span><strong data-qc-bs>0 pcs</strong><small data-qc-bs-dozen>0 lusin · 0 potong</small></div>
        <div class="qc-review-metric rework"><span>REWORK</span><strong data-qc-rework>0 pcs</strong><small data-qc-rework-dozen>0 lusin · 0 potong</small></div>
        <div class="qc-reviewed-total"><span>TOTAL DIPERIKSA</span><strong data-qc-total>0 pcs</strong><small data-qc-total-dozen>0 lusin · 0 potong</small></div>
        <div class="qc-check success" data-qc-check><span>✓</span><div><strong>Komposisi siap direview</strong><small>Good, BS, dan Rework dipisahkan.</small></div></div>
        <div class="qc-review-context"><span data-qc-review-ref>${qcJobs[0].ref}</span><b>•</b><span data-qc-review-product>${initialProduct.brand} ${initialProduct.sku}</span></div>
        <button class="primary-btn qc-review-button" type="button" data-qc-review>Review sebelum posting <span>→</span></button>
        <small class="qc-prototype-note">Prototype UX · belum menulis transaksi ke Supabase.</small>
      </aside>
    </section>

    <div class="qc-review-shield" data-qc-review-shield hidden></div>
    <section class="qc-review-sheet" data-qc-review-sheet hidden>
      <div class="qc-sheet-head"><div><span>REVIEW HASIL QC</span><strong data-qc-sheet-title>${initialProduct.brand} · ${initialProduct.sku}</strong></div><button type="button" data-qc-close>×</button></div>
      <div class="qc-sheet-flow">
        <div class="good"><span>Masuk FG</span><strong data-qc-sheet-good>0 pcs</strong><small data-qc-sheet-good-dozen>0 lusin · 0 potong</small></div>
        <div class="bs"><span>Barang BS</span><strong data-qc-sheet-bs>0 pcs</strong><small data-qc-sheet-bs-dozen>0 lusin · 0 potong</small></div>
        <div class="rework"><span>Rework</span><strong data-qc-sheet-rework>0 pcs</strong><small data-qc-sheet-rework-dozen>0 lusin · 0 potong</small></div>
      </div>
      <div class="qc-sheet-audit"><span>Tanggal fisik</span><strong data-qc-sheet-physical>—</strong><small>Waktu input sistem tetap terpisah untuk audit.</small></div>
      <div class="qc-sheet-actions"><button class="soft-btn" type="button" data-qc-close>Kembali edit</button><button class="primary-btn" type="button" data-qc-simulate>Simulasikan posting</button></div>
      <div class="qc-simulation-result" data-qc-simulation hidden><strong>Simulasi alur berhasil.</strong><span>Good akan membuat mutasi <b>QC → FG</b>; BS dan Rework masuk jalurnya masing-masing. Belum ada data backend yang diubah.</span></div>
    </section>
  `

  qcBind(root)
  qcRecalculate(root)
}

function qcCurrentProduct(root: HTMLElement) {
  const brand = root.querySelector<HTMLSelectElement>('[data-qc-brand]')?.value ?? qcProducts[0].brand
  const sku = root.querySelector<HTMLSelectElement>('[data-qc-sku]')?.value ?? qcProducts[0].sku
  return qcProducts.find((product) => product.brand === brand && product.sku === sku) ?? qcProducts[0]
}

function qcSetText(root: HTMLElement | Document, selector: string, text: string) {
  const element = root.querySelector<HTMLElement>(selector)
  if (element) element.textContent = text
}

function qcUpdateProduct(root: HTMLElement, keepValues = false) {
  const product = qcCurrentProduct(root)
  qcSetText(root, '[data-qc-product-brand]', product.brand)
  qcSetText(root, '[data-qc-product-sku]', product.sku)
  qcSetText(root, '[data-qc-product-name]', `${product.name} · ${product.color} · Range ${product.range}`)
  qcSetText(root, '[data-qc-warehouse]', product.warehouse)
  qcSetText(root, '[data-qc-review-product]', `${product.brand} ${product.sku}`)
  qcSetText(document, '[data-qc-sheet-title]', `${product.brand} · ${product.sku}`)

  const columns = Array.from(root.querySelectorAll<HTMLElement>('[data-qc-size-index]'))
  columns.forEach((column, index) => {
    const title = column.querySelector<HTMLElement>('.qc-size-head strong')
    if (title) title.textContent = product.sizes[index]
    if (!keepValues) {
      column.querySelectorAll<HTMLInputElement>('input[data-grade]').forEach((input) => { input.value = '0 pcs' })
    }
  })
  qcRecalculate(root)
}

function qcRecalculate(root: HTMLElement) {
  let goodTotal = 0
  let bsTotal = 0
  let reworkTotal = 0

  root.querySelectorAll<HTMLElement>('[data-qc-size-index]').forEach((column) => {
    let sizeTotal = 0
    column.querySelectorAll<HTMLInputElement>('input[data-grade]').forEach((input) => {
      const pcs = qcParseQty(input.value)
      const grade = input.dataset.grade ?? ''
      sizeTotal += pcs
      if (grade === 'good') goodTotal += pcs
      if (grade === 'bs') bsTotal += pcs
      if (grade === 'rework') reworkTotal += pcs
      qcSetText(column, `[data-conversion="${grade}"]`, qcDozenPieces(pcs))
    })
    qcSetText(column, '[data-size-total]', `${sizeTotal} pcs`)
    qcSetText(column, '[data-size-total-dozen]', qcDozenPieces(sizeTotal))
  })

  const total = goodTotal + bsTotal + reworkTotal
  qcSetText(root, '[data-qc-good]', `${goodTotal} pcs`)
  qcSetText(root, '[data-qc-good-dozen]', qcDozenPieces(goodTotal))
  qcSetText(root, '[data-qc-bs]', `${bsTotal} pcs`)
  qcSetText(root, '[data-qc-bs-dozen]', qcDozenPieces(bsTotal))
  qcSetText(root, '[data-qc-rework]', `${reworkTotal} pcs`)
  qcSetText(root, '[data-qc-rework-dozen]', qcDozenPieces(reworkTotal))
  qcSetText(root, '[data-qc-total]', `${total} pcs`)
  qcSetText(root, '[data-qc-total-dozen]', qcDozenPieces(total))

  qcSetText(document, '[data-qc-sheet-good]', `${goodTotal} pcs`)
  qcSetText(document, '[data-qc-sheet-good-dozen]', qcDozenPieces(goodTotal))
  qcSetText(document, '[data-qc-sheet-bs]', `${bsTotal} pcs`)
  qcSetText(document, '[data-qc-sheet-bs-dozen]', qcDozenPieces(bsTotal))
  qcSetText(document, '[data-qc-sheet-rework]', `${reworkTotal} pcs`)
  qcSetText(document, '[data-qc-sheet-rework-dozen]', qcDozenPieces(reworkTotal))

  const jobSelect = root.querySelector<HTMLSelectElement>('[data-qc-job]')
  const job = qcJobs[Number(jobSelect?.value ?? 0)] ?? qcJobs[0]
  const check = root.querySelector<HTMLElement>('[data-qc-check]')
  if (check) {
    const over = total > job.qty
    check.classList.toggle('success', !over && total > 0)
    check.classList.toggle('warn', over || total === 0)
    check.innerHTML = over
      ? `<span>!</span><div><strong>Jumlah melebihi sumber ${job.qty} pcs</strong><small>Cek kembali angka QC atau sumber PO.</small></div>`
      : total === 0
        ? `<span>!</span><div><strong>Belum ada hasil QC</strong><small>Isi minimal satu jumlah.</small></div>`
        : `<span>✓</span><div><strong>Komposisi siap direview</strong><small>${total} dari ${job.qty} pcs sumber tercatat.</small></div>`
  }
  const review = root.querySelector<HTMLButtonElement>('[data-qc-review]')
  if (review) review.disabled = total === 0 || total > job.qty
}

function qcOpenReview(root: HTMLElement) {
  const sheet = document.querySelector<HTMLElement>('[data-qc-review-sheet]')
  const shield = document.querySelector<HTMLElement>('[data-qc-review-shield]')
  const physical = root.querySelector<HTMLInputElement>('[data-qc-physical]')?.value ?? ''
  qcSetText(document, '[data-qc-sheet-physical]', physical ? physical.replace('T', ' · ') : '—')
  if (sheet) sheet.hidden = false
  if (shield) shield.hidden = false
  document.body.classList.add('qc-sheet-open')
}

function qcCloseReview() {
  const sheet = document.querySelector<HTMLElement>('[data-qc-review-sheet]')
  const shield = document.querySelector<HTMLElement>('[data-qc-review-shield]')
  if (sheet) sheet.hidden = true
  if (shield) shield.hidden = true
  document.body.classList.remove('qc-sheet-open')
}

function qcBind(root: HTMLElement) {
  root.addEventListener('input', (event) => {
    const target = event.target as HTMLInputElement | HTMLTextAreaElement | null
    if (!target) return
    if (target.matches('input[data-grade]')) qcRecalculate(root)
    if (target.matches('[data-qc-physical]')) sessionStorage.setItem('erp.qcPhysicalAt', target.value)
  })

  root.addEventListener('change', (event) => {
    const target = event.target as HTMLSelectElement | null
    if (!target) return
    if (target.matches('[data-qc-job]')) {
      const job = qcJobs[Number(target.value)] ?? qcJobs[0]
      qcSetText(root, '[data-qc-source]', job.source)
      qcSetText(root, '[data-qc-job-qty]', `${job.qty} pcs · ${qcDozenPieces(job.qty)}`)
      qcSetText(root, '[data-qc-mandor]', job.mandor)
      qcSetText(root, '[data-qc-review-ref]', job.ref)
      qcRecalculate(root)
    }
    if (target.matches('[data-qc-brand]')) {
      const skuSelect = root.querySelector<HTMLSelectElement>('[data-qc-sku]')
      if (skuSelect) skuSelect.innerHTML = qcProductOptions(target.value)
      qcUpdateProduct(root)
    }
    if (target.matches('[data-qc-sku]')) qcUpdateProduct(root, true)
  })

  root.querySelector<HTMLButtonElement>('[data-qc-zero]')?.addEventListener('click', () => {
    root.querySelectorAll<HTMLInputElement>('input[data-grade]').forEach((input) => { input.value = '0 pcs' })
    qcRecalculate(root)
  })
  root.querySelector<HTMLButtonElement>('[data-qc-review]')?.addEventListener('click', () => qcOpenReview(root))

  document.querySelectorAll<HTMLElement>('[data-qc-close], [data-qc-review-shield]').forEach((element) => element.addEventListener('click', qcCloseReview))
  document.querySelector<HTMLButtonElement>('[data-qc-simulate]')?.addEventListener('click', () => {
    const result = document.querySelector<HTMLElement>('[data-qc-simulation]')
    if (result) result.hidden = false
  })
}

function qcMountIfNeeded() {
  if (sessionStorage.getItem(qcActiveKey) !== qcPageId) return
  const placeholder = document.querySelector<HTMLElement>('.placeholder')
  if (!placeholder) return
  qcSetTopTitle(true)
  qcRender(placeholder)
}

document.addEventListener('click', (event) => {
  const target = event.target as Element | null
  const submenu = target?.closest('.submenu button') as HTMLButtonElement | null
  if (submenu) {
    const label = submenu.textContent?.replace(/^•\s*/, '').trim() ?? ''
    if (label === 'QC & Final SKU') {
      sessionStorage.setItem(qcActiveKey, qcPageId)
    } else {
      sessionStorage.removeItem(qcActiveKey)
      qcUnmount()
      qcCloseReview()
    }
  }
  const mainNav = target?.closest('.nav-main')
  if (mainNav && !submenu) {
    sessionStorage.removeItem(qcActiveKey)
    qcCloseReview()
  }
}, true)

const qcObserver = new MutationObserver(qcMountIfNeeded)
qcObserver.observe(document.documentElement, { childList: true, subtree: true })
queueMicrotask(qcMountIfNeeded)

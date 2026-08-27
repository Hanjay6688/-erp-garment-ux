const procurementActiveKey = 'erp.prototypePage'
const procurementPageId = 'procurement-receiving'

type Material = {
  code: string
  name: string
  category: 'Kain' | 'Aksesori'
  unit: 'meter' | 'pcs'
  stock: number
  lastCost: number
  detail: string
}

type Supplier = {
  name: string
  terms: string
  kind: string
}

const procurementMaterials: Material[] = [
  { code: 'FAB-DNM-12', name: 'Denim 12 oz · Dark Indigo', category: 'Kain', unit: 'meter', stock: 1840, lastCost: 48500, detail: 'Roll fabric · Gudang Bahan Utama' },
  { code: 'FAB-DNM-10', name: 'Denim 10 oz · Mid Blue', category: 'Kain', unit: 'meter', stock: 1120, lastCost: 43250, detail: 'Roll fabric · Gudang Bahan Utama' },
  { code: 'ACC-BTN-17', name: 'Kancing Jeans 17 mm · Gunmetal', category: 'Aksesori', unit: 'pcs', stock: 3860, lastCost: 1350, detail: 'Kancing depan · Rak A-03' },
  { code: 'ACC-ZIP-05', name: 'Zipper YKK #5 · Navy', category: 'Aksesori', unit: 'pcs', stock: 1420, lastCost: 6200, detail: 'Resleting celana · Rak A-05' },
  { code: 'ACC-RVT-09', name: 'Rivet Jeans 9 mm · Antique', category: 'Aksesori', unit: 'pcs', stock: 8240, lastCost: 750, detail: 'Rivet pocket · Rak A-04' },
  { code: 'ACC-LBL-01', name: 'Label Kulit Vivo · Brown', category: 'Aksesori', unit: 'pcs', stock: 940, lastCost: 2850, detail: 'Brand patch · Rak A-07' },
]

const procurementSuppliers: Supplier[] = [
  { name: 'PT Sumber Denim', terms: '30 hari', kind: 'Kain' },
  { name: 'CV Maju Aksesori', terms: '14 hari', kind: 'Aksesori' },
  { name: 'PT Prima Tekstil', terms: '30 hari', kind: 'Kain & finishing' },
]

const initialLines = [
  { code: 'FAB-DNM-12', ordered: 600, received: 594, rejected: 0, cost: 48500 },
  { code: 'ACC-BTN-17', ordered: 1200, received: 1200, rejected: 12, cost: 1350 },
]

function procurementMoney(value: number) {
  return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(Math.max(0, value || 0))
}

function procurementNumber(value: number) {
  return new Intl.NumberFormat('id-ID', { maximumFractionDigits: 2 }).format(Math.max(0, value || 0))
}

function procurementLocalDateTimeValue(date = new Date()) {
  const offsetMs = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16)
}

function procurementDateValue(date = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)) {
  const offsetMs = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 10)
}

function procurementSetTopTitle() {
  const topTitle = document.querySelector<HTMLElement>('.top-title')
  const strong = topTitle?.querySelector<HTMLElement>('strong')
  const sub = topTitle?.querySelector<HTMLElement>('span')
  if (!strong || !sub) return
  strong.textContent = 'Pembelian & Penerimaan'
  sub.textContent = 'Barang datang, nilai invoice, dan hutang supplier'
}

function procurementGenericPlaceholder(root: HTMLElement) {
  root.className = 'panel placeholder'
  root.removeAttribute('data-procurement-ready')
  root.innerHTML = '<div class="placeholder-icon">◇</div><h2>Fondasinya sudah disiapkan.</h2><p>Modul ini berikutnya akan mengikuti flow bisnis yang sama: informasi penting terlihat sebelum user menekan tombol yang mengubah uang atau stok.</p>'
}

function procurementUnmount() {
  const root = document.querySelector<HTMLElement>('.procurement-root')
  if (root) procurementGenericPlaceholder(root)
  procurementCloseReview()
}

function materialByCode(code: string) {
  return procurementMaterials.find((item) => item.code === code) ?? procurementMaterials[0]
}

function procurementLineTemplate(code: string, ordered = 0, received = 0, rejected = 0, cost?: number) {
  const item = materialByCode(code)
  return `<div class="proc-line" data-proc-line="${item.code}">
    <div class="proc-line-item">
      <span class="proc-category ${item.category === 'Kain' ? 'fabric' : 'accessory'}">${item.category}</span>
      <strong>${item.code}</strong>
      <small>${item.name}</small>
      <em>${item.detail}</em>
    </div>
    <label><span>Qty invoice</span><div class="proc-unit-input"><input data-proc-ordered type="number" min="0" step="1" value="${ordered}"/><b>${item.unit}</b></div></label>
    <label><span>Diterima fisik</span><div class="proc-unit-input"><input data-proc-received type="number" min="0" step="1" value="${received}"/><b>${item.unit}</b></div></label>
    <label><span>Reject / retur</span><div class="proc-unit-input"><input data-proc-rejected type="number" min="0" step="1" value="${rejected}"/><b>${item.unit}</b></div></label>
    <label><span>Harga / ${item.unit}</span><div class="proc-price-input"><span>Rp</span><input data-proc-cost type="number" min="0" step="1" value="${cost ?? item.lastCost}"/></div><small>Terakhir ${procurementMoney(item.lastCost)}</small></label>
    <div class="proc-line-value"><span>Nilai invoice</span><strong data-proc-line-invoice>Rp0</strong><small data-proc-line-received>Barang masuk Rp0</small></div>
    <button type="button" class="proc-remove" data-proc-remove aria-label="Hapus ${item.code}">×</button>
  </div>`
}

function procurementCatalogTemplate() {
  return procurementMaterials.map((item) => `<button type="button" class="proc-catalog-row" data-proc-add="${item.code}" data-proc-search="${item.category} ${item.code} ${item.name} ${item.detail}">
    <span class="proc-category ${item.category === 'Kain' ? 'fabric' : 'accessory'}">${item.category}</span>
    <div><strong>${item.code}</strong><small>${item.name}</small></div>
    <div class="proc-catalog-stock"><span>STOK</span><strong>${procurementNumber(item.stock)} ${item.unit}</strong></div>
    <div class="proc-catalog-cost"><span>HARGA TERAKHIR</span><strong>${procurementMoney(item.lastCost)}</strong></div>
    <b>＋</b>
  </button>`).join('')
}

function procurementRender(root: HTMLElement) {
  if (root.dataset.procurementReady === 'true') return
  root.dataset.procurementReady = 'true'
  root.className = 'procurement-root'
  const physicalAt = sessionStorage.getItem('erp.procurementPhysicalAt') || procurementLocalDateTimeValue()

  root.innerHTML = `
    <section class="hero-copy compact proc-hero">
      <div class="eyebrow">GUDANG · PROCUREMENT · HUTANG</div>
      <h1>Pembelian & penerimaan</h1>
      <p>Catat barang yang benar-benar datang. Qty invoice, penerimaan fisik, reject, harga, dan hutang supplier tetap terlihat sebagai angka yang berbeda.</p>
    </section>

    <section class="proc-layout">
      <div class="panel proc-workbench">
        <section class="proc-section">
          <div class="proc-section-head"><div><span>01</span><div><strong>Supplier & dokumen</strong><small>Pisahkan waktu barang datang dari waktu staf menginput.</small></div></div><span class="proc-status">DRAFT · SIMULASI</span></div>
          <div class="proc-doc-grid">
            <label class="field"><span>Supplier</span><select data-proc-supplier>${procurementSuppliers.map((supplier, i) => `<option value="${i}">${supplier.name}</option>`).join('')}</select><small data-proc-supplier-meta>${procurementSuppliers[0].kind} · tempo ${procurementSuppliers[0].terms}</small></label>
            <label class="field"><span>No. invoice supplier</span><input data-proc-invoice value="SD-0827-177" placeholder="Nomor dari supplier"/></label>
            <label class="field"><span>Tanggal & jam barang diterima</span><input data-proc-physical type="datetime-local" value="${physicalAt}"/><small>Ini waktu bisnis/fisik.</small></label>
            <label class="field"><span>Jatuh tempo</span><input data-proc-due type="date" value="${procurementDateValue()}"/></label>
            <label class="field"><span>Masuk ke lokasi</span><select data-proc-location><option>Gudang Bahan Utama</option><option>Gudang Aksesori</option><option>Area Karantina / Reject</option></select></label>
            <label class="field"><span>Status pembayaran</span><select data-proc-payment><option value="credit">Tempo · bentuk hutang</option><option value="cash">Dibayar langsung</option></select></label>
          </div>
        </section>

        <section class="proc-section proc-items-section">
          <div class="proc-section-head"><div><span>02</span><div><strong>Barang yang datang</strong><small>Satu invoice boleh kain + aksesori. Harga boleh beda dari harga terakhir.</small></div></div><button type="button" class="soft-btn" data-proc-open-catalog>＋ Tambah barang</button></div>
          <div class="proc-line-head"><span>BARANG</span><span>QTY INVOICE</span><span>DITERIMA</span><span>REJECT</span><span>HARGA</span><span>NILAI</span><span></span></div>
          <div class="proc-lines" data-proc-lines>
            ${initialLines.map((line) => procurementLineTemplate(line.code, line.ordered, line.received, line.rejected, line.cost)).join('')}
          </div>
          <div class="proc-empty" data-proc-empty hidden>Belum ada barang. Tambahkan item dari katalog bahan/aksesori.</div>
        </section>

        <section class="proc-section proc-note-section">
          <div class="proc-note-grid">
            <label class="field"><span>Catatan penerimaan · opsional</span><textarea data-proc-note placeholder="Contoh: kain kurang 6 meter, supplier janji kirim susulan"></textarea></label>
            <div class="proc-audit-note"><span>JEJAK AUDIT NANTI</span><strong>Waktu fisik ≠ waktu input sistem</strong><small>Frontend ini belum terhubung backend. Saat live, keduanya harus disimpan terpisah.</small></div>
          </div>
        </section>
      </div>

      <aside class="panel proc-summary">
        <div class="eyebrow">RINGKASAN PEMBELIAN</div>
        <h2>Uang & stok yang akan bergerak</h2>
        <div class="proc-summary-metric"><span>NILAI INVOICE SUPPLIER</span><strong data-proc-total-invoice>Rp0</strong><small>Dasar hutang / pembayaran</small></div>
        <div class="proc-summary-metric received"><span>NILAI BARANG DITERIMA</span><strong data-proc-total-received>Rp0</strong><small>Masuk persediaan sesuai qty fisik</small></div>
        <div class="proc-summary-metric variance"><span>SELISIH PENERIMAAN</span><strong data-proc-variance>0 unit</strong><small data-proc-variance-note>Sesuai invoice</small></div>
        <div class="proc-payable-box"><span data-proc-payable-label>HUTANG SUPPLIER AKAN TERBENTUK</span><strong data-proc-payable>Rp0</strong><small data-proc-due-copy>Jatuh tempo —</small></div>
        <div class="proc-check" data-proc-check><span>✓</span><div><strong>Siap direview</strong><small>Semua nilai utama sudah terbaca.</small></div></div>
        <button type="button" class="primary-btn proc-review-button" data-proc-review>Review penerimaan <span>→</span></button>
        <small class="proc-prototype-note">Prototype frontend · tidak menulis stok, hutang, kas, atau jurnal.</small>
      </aside>
    </section>

    <section class="panel proc-history">
      <div class="panel-head"><div><div class="eyebrow">PENERIMAAN TERBARU · SIMULASI</div><h2>Invoice yang perlu diperhatikan</h2></div><button class="soft-btn" type="button">Semua penerimaan</button></div>
      <div class="proc-history-row"><span class="proc-history-date">27 Agu<br/><b>10:15</b></span><div><strong>PT Sumber Denim</strong><small>SD-0827-171 · Kain denim</small></div><div><span>DITERIMA</span><strong>1.180 meter</strong></div><div><span>SELISIH</span><strong class="warn">-20 meter</strong></div><div><span>HUTANG</span><strong>Rp57,4 jt</strong></div><span class="proc-history-pill warn">KIRIM SUSULAN</span></div>
      <div class="proc-history-row"><span class="proc-history-date">26 Agu<br/><b>15:42</b></span><div><strong>CV Maju Aksesori</strong><small>MA-260826-088 · Kancing + zipper</small></div><div><span>DITERIMA</span><strong>3.600 pcs</strong></div><div><span>SELISIH</span><strong>0 pcs</strong></div><div><span>HUTANG</span><strong>Rp11,8 jt</strong></div><span class="proc-history-pill good">LENGKAP</span></div>
    </section>

    <div class="proc-catalog-shield" data-proc-catalog-shield hidden></div>
    <section class="proc-catalog-sheet" data-proc-catalog-sheet hidden>
      <div class="proc-sheet-head"><div><span>KATALOG BAHAN & AKSESORI</span><strong>Tambah ke invoice</strong></div><button type="button" data-proc-close-catalog>×</button></div>
      <div class="proc-search"><span>⌕</span><input data-proc-search-input placeholder="Cari kode, bahan, aksesori..."/></div>
      <div class="proc-catalog-list" data-proc-catalog-list>${procurementCatalogTemplate()}</div>
    </section>

    <div class="proc-review-shield" data-proc-review-shield hidden></div>
    <section class="proc-review-sheet" data-proc-review-sheet hidden>
      <div class="proc-sheet-head"><div><span>REVIEW SEBELUM POSTING</span><strong data-proc-review-title>PT Sumber Denim · SD-0827-177</strong></div><button type="button" data-proc-close-review>×</button></div>
      <div class="proc-review-flow">
        <div><span>Invoice supplier</span><strong data-proc-review-invoice>Rp0</strong><small>Nilai kewajiban supplier</small></div>
        <div><span>Barang diterima</span><strong data-proc-review-received>Rp0</strong><small>Nilai stok yang masuk</small></div>
        <div><span>Selisih fisik</span><strong data-proc-review-variance>0 unit</strong><small>Harus punya alasan bila tidak nol</small></div>
      </div>
      <div class="proc-review-audit"><span>Tanggal fisik penerimaan</span><strong data-proc-review-physical>—</strong><small>Waktu input sistem akan dicatat terpisah saat backend disambungkan.</small></div>
      <div class="proc-sheet-actions"><button class="soft-btn" type="button" data-proc-close-review>Kembali edit</button><button class="primary-btn" type="button" data-proc-simulate>Simulasikan posting</button></div>
      <div class="proc-simulation" data-proc-simulation hidden><strong>Simulasi aman.</strong><span>Saat live nanti: qty diterima → stok bahan/aksesori, invoice → hutang supplier, dan semua jejak tanggal/audit tetap terpisah. Belum ada backend yang diubah.</span></div>
    </section>
  `

  procurementBind(root)
  procurementRecalculate(root)
}

function readNumber(input: HTMLInputElement | null) {
  if (!input) return 0
  const value = Number(input.value)
  return Number.isFinite(value) ? Math.max(0, value) : 0
}

function procurementRecalculate(root: HTMLElement) {
  let invoiceTotal = 0
  let receivedTotal = 0
  let varianceUnits = 0
  let invalidReject = false
  let hasLines = false

  root.querySelectorAll<HTMLElement>('[data-proc-line]').forEach((line) => {
    hasLines = true
    const ordered = readNumber(line.querySelector<HTMLInputElement>('[data-proc-ordered]'))
    const received = readNumber(line.querySelector<HTMLInputElement>('[data-proc-received]'))
    const rejected = readNumber(line.querySelector<HTMLInputElement>('[data-proc-rejected]'))
    const cost = readNumber(line.querySelector<HTMLInputElement>('[data-proc-cost]'))
    const invoiceValue = ordered * cost
    const accepted = Math.max(0, received - rejected)
    const receivedValue = accepted * cost
    invoiceTotal += invoiceValue
    receivedTotal += receivedValue
    varianceUnits += received - ordered
    if (rejected > received) invalidReject = true
    const invoiceNode = line.querySelector<HTMLElement>('[data-proc-line-invoice]')
    const receivedNode = line.querySelector<HTMLElement>('[data-proc-line-received]')
    if (invoiceNode) invoiceNode.textContent = procurementMoney(invoiceValue)
    if (receivedNode) receivedNode.textContent = `Barang masuk ${procurementMoney(receivedValue)}${rejected ? ` · reject ${procurementNumber(rejected)}` : ''}`
    line.classList.toggle('has-variance', received !== ordered || rejected > 0)
  })

  const totalInvoice = root.querySelector<HTMLElement>('[data-proc-total-invoice]')
  const totalReceived = root.querySelector<HTMLElement>('[data-proc-total-received]')
  const variance = root.querySelector<HTMLElement>('[data-proc-variance]')
  const varianceNote = root.querySelector<HTMLElement>('[data-proc-variance-note]')
  const payable = root.querySelector<HTMLElement>('[data-proc-payable]')
  const payableLabel = root.querySelector<HTMLElement>('[data-proc-payable-label]')
  const dueCopy = root.querySelector<HTMLElement>('[data-proc-due-copy]')
  const payment = root.querySelector<HTMLSelectElement>('[data-proc-payment]')?.value ?? 'credit'
  const due = root.querySelector<HTMLInputElement>('[data-proc-due]')?.value ?? ''

  if (totalInvoice) totalInvoice.textContent = procurementMoney(invoiceTotal)
  if (totalReceived) totalReceived.textContent = procurementMoney(receivedTotal)
  if (variance) variance.textContent = `${varianceUnits > 0 ? '+' : ''}${procurementNumber(varianceUnits)} unit`
  if (varianceNote) varianceNote.textContent = varianceUnits === 0 ? 'Qty fisik sesuai invoice' : varianceUnits < 0 ? 'Barang datang kurang dari invoice' : 'Barang datang lebih dari invoice'
  if (payable) payable.textContent = procurementMoney(invoiceTotal)
  if (payableLabel) payableLabel.textContent = payment === 'credit' ? 'HUTANG SUPPLIER AKAN TERBENTUK' : 'PEMBAYARAN LANGSUNG'
  if (dueCopy) dueCopy.textContent = payment === 'credit' ? `Jatuh tempo ${due || '—'}` : 'Kas / bank akan dipilih saat posting live nanti'

  const empty = root.querySelector<HTMLElement>('[data-proc-empty]')
  if (empty) empty.hidden = hasLines
  const check = root.querySelector<HTMLElement>('[data-proc-check]')
  const review = root.querySelector<HTMLButtonElement>('[data-proc-review]')
  const invoiceRef = root.querySelector<HTMLInputElement>('[data-proc-invoice]')?.value.trim() ?? ''
  const note = root.querySelector<HTMLTextAreaElement>('[data-proc-note]')?.value.trim() ?? ''
  const needsVarianceReason = varianceUnits !== 0 && note.length < 4
  const blocked = !hasLines || invoiceTotal <= 0 || invalidReject || !invoiceRef || needsVarianceReason

  if (check) {
    check.className = `proc-check ${blocked ? 'warn' : 'success'}`
    check.innerHTML = invalidReject
      ? '<span>!</span><div><strong>Reject melebihi barang diterima</strong><small>Periksa angka penerimaan.</small></div>'
      : !invoiceRef
        ? '<span>!</span><div><strong>Nomor invoice belum diisi</strong><small>Referensi supplier wajib jelas.</small></div>'
        : needsVarianceReason
          ? '<span>!</span><div><strong>Ada selisih fisik</strong><small>Tulis alasan / rencana tindak lanjut di catatan.</small></div>'
          : !hasLines
            ? '<span>!</span><div><strong>Belum ada barang</strong><small>Tambahkan minimal satu item.</small></div>'
            : '<span>✓</span><div><strong>Siap direview</strong><small>Nilai invoice, penerimaan, dan selisih sudah terbaca.</small></div>'
  }
  if (review) review.disabled = blocked

  document.querySelectorAll<HTMLElement>('[data-proc-review-invoice]').forEach((node) => { node.textContent = procurementMoney(invoiceTotal) })
  document.querySelectorAll<HTMLElement>('[data-proc-review-received]').forEach((node) => { node.textContent = procurementMoney(receivedTotal) })
  document.querySelectorAll<HTMLElement>('[data-proc-review-variance]').forEach((node) => { node.textContent = `${varianceUnits > 0 ? '+' : ''}${procurementNumber(varianceUnits)} unit` })
}

function procurementOpenCatalog() {
  const sheet = document.querySelector<HTMLElement>('[data-proc-catalog-sheet]')
  const shield = document.querySelector<HTMLElement>('[data-proc-catalog-shield]')
  if (sheet) sheet.hidden = false
  if (shield) shield.hidden = false
  document.body.classList.add('proc-sheet-open')
  document.querySelector<HTMLInputElement>('[data-proc-search-input]')?.focus()
}

function procurementCloseCatalog() {
  const sheet = document.querySelector<HTMLElement>('[data-proc-catalog-sheet]')
  const shield = document.querySelector<HTMLElement>('[data-proc-catalog-shield]')
  if (sheet) sheet.hidden = true
  if (shield) shield.hidden = true
  if (document.querySelector<HTMLElement>('[data-proc-review-sheet]')?.hidden !== false) document.body.classList.remove('proc-sheet-open')
}

function procurementOpenReview(root: HTMLElement) {
  const supplierIndex = Number(root.querySelector<HTMLSelectElement>('[data-proc-supplier]')?.value ?? 0)
  const supplier = procurementSuppliers[supplierIndex] ?? procurementSuppliers[0]
  const invoice = root.querySelector<HTMLInputElement>('[data-proc-invoice]')?.value.trim() ?? '—'
  const physical = root.querySelector<HTMLInputElement>('[data-proc-physical]')?.value ?? ''
  const title = document.querySelector<HTMLElement>('[data-proc-review-title]')
  const physicalNode = document.querySelector<HTMLElement>('[data-proc-review-physical]')
  if (title) title.textContent = `${supplier.name} · ${invoice}`
  if (physicalNode) physicalNode.textContent = physical ? physical.replace('T', ' · ') : '—'
  const sheet = document.querySelector<HTMLElement>('[data-proc-review-sheet]')
  const shield = document.querySelector<HTMLElement>('[data-proc-review-shield]')
  if (sheet) sheet.hidden = false
  if (shield) shield.hidden = false
  document.body.classList.add('proc-sheet-open')
}

function procurementCloseReview() {
  const sheet = document.querySelector<HTMLElement>('[data-proc-review-sheet]')
  const shield = document.querySelector<HTMLElement>('[data-proc-review-shield]')
  if (sheet) sheet.hidden = true
  if (shield) shield.hidden = true
  const simulation = document.querySelector<HTMLElement>('[data-proc-simulation]')
  if (simulation) simulation.hidden = true
  if (document.querySelector<HTMLElement>('[data-proc-catalog-sheet]')?.hidden !== false) document.body.classList.remove('proc-sheet-open')
}

function procurementBind(root: HTMLElement) {
  root.addEventListener('input', (event) => {
    const target = event.target as HTMLInputElement | HTMLTextAreaElement | null
    if (!target) return
    if (target.matches('[data-proc-physical]')) sessionStorage.setItem('erp.procurementPhysicalAt', target.value)
    procurementRecalculate(root)
  })

  root.addEventListener('change', (event) => {
    const target = event.target as HTMLSelectElement | null
    if (!target) return
    if (target.matches('[data-proc-supplier]')) {
      const supplier = procurementSuppliers[Number(target.value)] ?? procurementSuppliers[0]
      const meta = root.querySelector<HTMLElement>('[data-proc-supplier-meta]')
      if (meta) meta.textContent = `${supplier.kind} · tempo ${supplier.terms}`
    }
    procurementRecalculate(root)
  })

  root.addEventListener('click', (event) => {
    const target = event.target as Element | null
    if (target?.closest('[data-proc-open-catalog]')) procurementOpenCatalog()
    const remove = target?.closest('[data-proc-remove]') as HTMLButtonElement | null
    if (remove) {
      remove.closest('[data-proc-line]')?.remove()
      procurementRecalculate(root)
    }
    if (target?.closest('[data-proc-review]')) procurementOpenReview(root)
  })

  document.querySelectorAll<HTMLElement>('[data-proc-close-catalog], [data-proc-catalog-shield]').forEach((node) => node.addEventListener('click', procurementCloseCatalog))
  document.querySelectorAll<HTMLElement>('[data-proc-close-review], [data-proc-review-shield]').forEach((node) => node.addEventListener('click', procurementCloseReview))
  document.querySelector<HTMLElement>('[data-proc-catalog-list]')?.addEventListener('click', (event) => {
    const target = event.target as Element | null
    const add = target?.closest<HTMLButtonElement>('[data-proc-add]')
    if (!add) return
    const code = add.dataset.procAdd
    if (!code) return
    const lines = root.querySelector<HTMLElement>('[data-proc-lines]')
    const existing = root.querySelector(`[data-proc-line="${code}"]`)
    if (!existing && lines) lines.insertAdjacentHTML('beforeend', procurementLineTemplate(code, 0, 0, 0))
    procurementCloseCatalog()
    procurementRecalculate(root)
  })
  document.querySelector<HTMLInputElement>('[data-proc-search-input]')?.addEventListener('input', (event) => {
    const query = (event.currentTarget as HTMLInputElement).value.toLowerCase()
    document.querySelectorAll<HTMLElement>('[data-proc-search]').forEach((row) => {
      row.hidden = !(row.dataset.procSearch ?? '').toLowerCase().includes(query)
    })
  })
  document.querySelector<HTMLButtonElement>('[data-proc-simulate]')?.addEventListener('click', () => {
    const result = document.querySelector<HTMLElement>('[data-proc-simulation]')
    if (result) result.hidden = false
  })
}

function procurementMountIfNeeded() {
  if (sessionStorage.getItem(procurementActiveKey) !== procurementPageId) return
  const placeholder = document.querySelector<HTMLElement>('.placeholder')
  if (!placeholder) return
  procurementSetTopTitle()
  procurementRender(placeholder)
}

document.addEventListener('click', (event) => {
  const target = event.target as Element | null
  const submenu = target?.closest('.submenu button') as HTMLButtonElement | null
  if (submenu) {
    const label = submenu.textContent?.replace(/^•\s*/, '').trim() ?? ''
    if (label === 'Pembelian & Penerimaan') {
      sessionStorage.setItem(procurementActiveKey, procurementPageId)
    } else if (sessionStorage.getItem(procurementActiveKey) === procurementPageId) {
      sessionStorage.removeItem(procurementActiveKey)
      procurementUnmount()
    }
  }
  const mainNav = target?.closest('.nav-main')
  if (mainNav && !submenu && sessionStorage.getItem(procurementActiveKey) === procurementPageId) {
    sessionStorage.removeItem(procurementActiveKey)
    procurementUnmount()
  }
}, true)

const procurementObserver = new MutationObserver(procurementMountIfNeeded)
procurementObserver.observe(document.documentElement, { childList: true, subtree: true })
queueMicrotask(procurementMountIfNeeded)

import {
  createAndPostQc,
  getQcEntryContext,
  sendInternalMagicLink,
  supabase,
  type CreateQcPayload,
  type QcEntryContext,
  type QcLiveSource,
} from './supabase-live'

const liveRequestKey = 'erp.qcLiveRequestId'
let contextCache: QcEntryContext | null = null
let contextPromise: Promise<QcEntryContext> | null = null

function parseQty(value: string) {
  const normalized = value.toLowerCase().replace(',', '.')
  const dozenMatch = normalized.match(/([0-9]+(?:\.[0-9]+)?)\s*(?:lusin|lsn|dozen)/)
  const pcsMatch = normalized.match(/([0-9]+(?:\.[0-9]+)?)\s*(?:pcs|pc|piece|biji|potong|ptg)/)
  if (dozenMatch || pcsMatch) {
    return Math.max(0, Math.round((dozenMatch ? Number(dozenMatch[1]) * 12 : 0) + (pcsMatch ? Number(pcsMatch[1]) : 0)))
  }
  const plain = Number(normalized.replace(/[^0-9.]/g, ''))
  return Number.isNaN(plain) ? 0 : Math.max(0, Math.round(plain))
}

function setStatus(root: HTMLElement, tone: 'idle' | 'good' | 'warn' | 'bad', title: string, detail: string) {
  const status = root.querySelector<HTMLElement>('[data-qc-live-status]')
  if (!status) return
  status.className = `qc-live-status ${tone}`
  status.innerHTML = `<span class="qc-live-dot"></span><div><strong>${title}</strong><small>${detail}</small></div>`
}

function setLiveResult(tone: 'good' | 'warn' | 'bad', title: string, detail: string) {
  const result = document.querySelector<HTMLElement>('[data-qc-live-result]')
  if (!result) return
  result.hidden = false
  result.className = `qc-live-result ${tone}`
  result.innerHTML = `<strong>${title}</strong><span>${detail}</span>`
}

function authPanel(show: boolean) {
  const panel = document.querySelector<HTMLElement>('[data-qc-live-auth]')
  if (panel) panel.hidden = !show
}

async function getContextFresh() {
  if (contextCache) return contextCache
  if (!contextPromise) {
    contextPromise = getQcEntryContext().then((context) => {
      contextCache = context
      return context
    }).finally(() => { contextPromise = null })
  }
  return contextPromise
}

async function refreshLiveStatus(root: HTMLElement) {
  setStatus(root, 'idle', 'Supabase siap', 'Mengecek session internal…')
  const { data: { session } } = await supabase.auth.getSession()
  if (!session) {
    setStatus(root, 'warn', 'Posting live terkunci', 'Login internal diperlukan. Preview UX tetap bisa dipakai.')
    const note = root.querySelector<HTMLElement>('.qc-prototype-note')
    if (note) note.textContent = 'Preview data masih simulasi · posting live hanya untuk user ERP terautentikasi.'
    return
  }

  try {
    const context = await getContextFresh()
    const sourceCount = context.sources?.length ?? 0
    const productCount = context.products?.length ?? 0
    const locationCount = context.locations?.length ?? 0
    if (!sourceCount || !productCount || !locationCount) {
      setStatus(root, 'warn', `Backend live · ${context.role ?? 'internal'}`, `Master/PO belum lengkap: ${sourceCount} sumber QC · ${productCount} SKU-size · ${locationCount} gudang FG.`)
    } else {
      setStatus(root, 'good', `Backend live · ${context.role ?? 'internal'}`, `${sourceCount} sumber QC · ${productCount} SKU-size · ${locationCount} gudang FG siap.`)
    }
    const note = root.querySelector<HTMLElement>('.qc-prototype-note')
    if (note) note.textContent = 'Posting memakai RPC atomic + idempotency. Preview baru berubah jadi data live saat master/PO tersedia.'
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    setStatus(root, 'bad', 'Session ada, akses ERP belum siap', message.includes('Internal ERP access required') ? 'Akun login belum dipetakan ke app_users ERP.' : message)
  }
}

function chooseSource(context: QcEntryContext, root: HTMLElement) {
  const poNumber = root.querySelector<HTMLElement>('[data-qc-review-ref]')?.textContent?.trim() ?? ''
  const selectedText = root.querySelector<HTMLSelectElement>('[data-qc-job]')?.selectedOptions[0]?.textContent ?? ''
  let candidates = context.sources.filter((source) => source.po_number === poNumber)
  if (candidates.length > 1) {
    const byExecutor = candidates.filter((source) => selectedText.toLowerCase().includes(source.executor_name.toLowerCase()))
    if (byExecutor.length === 1) candidates = byExecutor
  }
  if (candidates.length === 0) throw new Error(`PO ${poNumber || 'terpilih'} belum punya sumber QC live.`)
  if (candidates.length > 1) throw new Error(`PO ${poNumber} punya lebih dari satu sumber QC. Pilihan sumber live harus dibuat lebih spesifik sebelum posting.`)
  return candidates[0]
}

function buildPayload(context: QcEntryContext, root: HTMLElement, source: QcLiveSource): CreateQcPayload {
  const brand = root.querySelector<HTMLElement>('[data-qc-product-brand]')?.textContent?.trim() ?? ''
  const sku = root.querySelector<HTMLElement>('[data-qc-product-sku]')?.textContent?.trim() ?? ''
  const warehouseName = root.querySelector<HTMLElement>('[data-qc-warehouse]')?.textContent?.trim() ?? ''
  const physicalValue = root.querySelector<HTMLInputElement>('[data-qc-physical]')?.value ?? ''
  const physicalDate = new Date(physicalValue)
  if (!physicalValue || Number.isNaN(physicalDate.getTime())) throw new Error('Tanggal & jam fisik belum valid.')

  let destination = context.locations.find((location) => location.location_name === warehouseName)
  if (!destination && context.locations.length === 1) destination = context.locations[0]
  if (!destination) throw new Error(`Gudang FG “${warehouseName || 'terpilih'}” belum cocok dengan lokasi live.`)

  const globalNote = root.querySelector<HTMLTextAreaElement>('[data-qc-note]')?.value.trim() ?? ''
  const items = Array.from(root.querySelectorAll<HTMLElement>('[data-qc-size-index]')).map((column) => {
    const size = column.querySelector<HTMLElement>('.qc-size-head strong')?.textContent?.trim() ?? ''
    const product = context.products.find((row) => row.model_id === source.model_id && row.brand_name === brand && row.sku === sku && row.size_code === size)
    if (!product) throw new Error(`${brand} SKU ${sku} size ${size} belum punya product_id live yang sesuai PO.`)
    const qtyGood = parseQty(column.querySelector<HTMLInputElement>('input[data-grade="good"]')?.value ?? '0')
    const qtyBs = parseQty(column.querySelector<HTMLInputElement>('input[data-grade="bs"]')?.value ?? '0')
    const qtyRework = parseQty(column.querySelector<HTMLInputElement>('input[data-grade="rework"]')?.value ?? '0')
    return {
      cutting_group_id: source.cutting_group_id,
      source_laundry_receipt_line_id: source.source_laundry_receipt_line_id,
      final_product_id: product.product_id,
      qty_good_pcs: qtyGood,
      qty_bs_pcs: qtyBs,
      qty_rework_pcs: qtyRework,
      notes: globalNote || null,
    }
  })

  const total = items.reduce((sum, item) => sum + item.qty_good_pcs + item.qty_bs_pcs + item.qty_rework_pcs, 0)
  if (total <= 0) throw new Error('Belum ada hasil QC untuk diposting.')
  if (total > Number(source.available_qty_pcs)) throw new Error(`Total QC ${total} pcs melebihi sumber live ${source.available_qty_pcs} pcs.`)

  let requestId = sessionStorage.getItem(liveRequestKey)
  if (!requestId) {
    requestId = crypto.randomUUID()
    sessionStorage.setItem(liveRequestKey, requestId)
  }

  return {
    p_request_id: requestId,
    p_po_id: source.po_id,
    p_destination_location_id: destination.id,
    p_physical_at: physicalDate.toISOString(),
    p_notes: globalNote || null,
    p_items: items,
  }
}

async function postLive(root: HTMLElement, button: HTMLButtonElement) {
  const { data: { session } } = await supabase.auth.getSession()
  if (!session) {
    authPanel(true)
    setLiveResult('warn', 'Login internal diperlukan', 'Kirim link login ke email user ERP, lalu kembali ke halaman ini untuk posting.')
    return
  }

  button.disabled = true
  const originalText = button.textContent
  button.textContent = 'Memvalidasi backend…'
  try {
    const context = await getContextFresh()
    if (!context.sources.length || !context.products.length || !context.locations.length) {
      throw new Error('Backend sudah tersambung, tetapi master data / PO / gudang FG belum tersedia untuk transaksi live.')
    }
    const source = chooseSource(context, root)
    const payload = buildPayload(context, root, source)
    button.textContent = 'Posting QC…'
    const result = await createAndPostQc(payload)
    sessionStorage.removeItem(liveRequestKey)
    contextCache = null
    setLiveResult('good', `${result.inspection_number} · ${result.status}`, result.idempotent_replay ? 'Request ini sebelumnya sudah berhasil; backend mengembalikan hasil yang sama tanpa posting ganda.' : 'Good sudah masuk FG; BS + Rework masuk kasus BS untuk routing berikutnya. HPP dan audit ikut diposting oleh backend.')
    button.textContent = 'QC sudah diposting ✓'
    await refreshLiveStatus(root)
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    setLiveResult('bad', 'Posting dibatalkan', message)
    button.disabled = false
    button.textContent = originalText || 'Posting ke Supabase'
  }
}

async function sendLogin(button: HTMLButtonElement) {
  const input = document.querySelector<HTMLInputElement>('[data-qc-live-email]')
  const email = input?.value.trim() ?? ''
  if (!email || !email.includes('@')) {
    setLiveResult('warn', 'Email belum valid', 'Masukkan email user internal ERP.')
    return
  }
  button.disabled = true
  const original = button.textContent
  button.textContent = 'Mengirim…'
  try {
    await sendInternalMagicLink(email)
    setLiveResult('good', 'Link login dikirim', 'Buka email di perangkat ini. User baru tidak dibuat otomatis; hanya akun Auth yang sudah disiapkan yang bisa masuk.')
    button.textContent = 'Link terkirim ✓'
  } catch (error) {
    setLiveResult('bad', 'Login belum bisa dikirim', error instanceof Error ? error.message : String(error))
    button.disabled = false
    button.textContent = original || 'Kirim link login'
  }
}

function upgradeReviewButton(root: HTMLElement) {
  const oldButton = document.querySelector<HTMLButtonElement>('[data-qc-simulate]')
  if (!oldButton || oldButton.dataset.liveButton === 'true') return
  const button = oldButton.cloneNode(true) as HTMLButtonElement
  button.dataset.liveButton = 'true'
  button.textContent = 'Posting ke Supabase'
  oldButton.replaceWith(button)
  button.addEventListener('click', () => void postLive(root, button))
}

function injectLiveUi(root: HTMLElement) {
  if (root.dataset.qcLiveReady === 'true') return
  root.dataset.qcLiveReady = 'true'

  const reviewCard = root.querySelector<HTMLElement>('.qc-review-card')
  const heading = reviewCard?.querySelector('h2')
  if (reviewCard && heading) {
    const status = document.createElement('div')
    status.dataset.qcLiveStatus = 'true'
    status.className = 'qc-live-status idle'
    status.innerHTML = '<span class="qc-live-dot"></span><div><strong>Supabase siap</strong><small>Mengecek session internal…</small></div>'
    heading.insertAdjacentElement('afterend', status)
  }

  const sheet = document.querySelector<HTMLElement>('[data-qc-review-sheet]')
  const actions = sheet?.querySelector<HTMLElement>('.qc-sheet-actions')
  if (sheet && actions) {
    const auth = document.createElement('div')
    auth.dataset.qcLiveAuth = 'true'
    auth.className = 'qc-live-auth'
    auth.hidden = true
    auth.innerHTML = '<div><span>LOGIN INTERNAL</span><strong>Masuk sebelum posting live</strong><small>Magic link tidak membuat user baru otomatis.</small></div><div class="qc-live-auth-controls"><input type="email" inputmode="email" autocomplete="email" placeholder="email user ERP" data-qc-live-email/><button type="button" class="soft-btn" data-qc-live-login>Kirim link login</button></div>'
    actions.insertAdjacentElement('beforebegin', auth)

    const result = document.createElement('div')
    result.dataset.qcLiveResult = 'true'
    result.className = 'qc-live-result'
    result.hidden = true
    actions.insertAdjacentElement('afterend', result)

    auth.querySelector<HTMLButtonElement>('[data-qc-live-login]')?.addEventListener('click', (event) => void sendLogin(event.currentTarget as HTMLButtonElement))
  }

  root.addEventListener('input', () => sessionStorage.removeItem(liveRequestKey))
  root.addEventListener('change', () => sessionStorage.removeItem(liveRequestKey))
  upgradeReviewButton(root)
  void refreshLiveStatus(root)
}

function mountBridge() {
  const root = document.querySelector<HTMLElement>('.qc-prototype-root')
  if (!root) return
  injectLiveUi(root)
}

supabase.auth.onAuthStateChange(() => {
  contextCache = null
  queueMicrotask(() => {
    const root = document.querySelector<HTMLElement>('.qc-prototype-root')
    if (root) void refreshLiveStatus(root)
  })
})

const observer = new MutationObserver(mountBridge)
observer.observe(document.documentElement, { childList: true, subtree: true })
queueMicrotask(mountBridge)

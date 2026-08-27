const physicalDateStorageKey = 'erp.physicalTransactionAt'

function localDateTimeValue(date = new Date()) {
  const offsetMs = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16)
}

function toggleMutationRow(row: Element, force?: boolean) {
  const expanded = force ?? !row.classList.contains('is-expanded')
  row.classList.toggle('is-expanded', expanded)
  row.setAttribute('aria-expanded', String(expanded))
  const button = row.querySelector<HTMLButtonElement>('.compact-detail-toggle')
  if (button) {
    button.textContent = expanded ? 'Tutup rincian' : 'Lihat rincian'
    button.setAttribute('aria-expanded', String(expanded))
  }
}

function enhanceMutationRows() {
  document.querySelectorAll<HTMLElement>('.mutation-row').forEach((row) => {
    if (row.dataset.compactReady === 'true') return
    row.dataset.compactReady = 'true'
    row.classList.add('mutation-collapsible')
    row.setAttribute('role', 'button')
    row.setAttribute('tabindex', '0')
    row.setAttribute('aria-expanded', 'false')

    const totalChange = row.querySelector<HTMLElement>('.mutation-total .total-book-step.change strong')?.textContent?.trim() ?? '—'
    const totalClosing = row.querySelector<HTMLElement>('.mutation-total .total-book-step.closing strong')?.textContent?.trim() ?? '—'

    const summary = document.createElement('div')
    summary.className = 'compact-book-summary'
    summary.innerHTML = `<span><small>MUTASI</small><strong>${totalChange}</strong></span><span><small>SALDO AKHIR</small><strong>${totalClosing}</strong></span>`

    const toggle = document.createElement('button')
    toggle.type = 'button'
    toggle.className = 'compact-detail-toggle'
    toggle.textContent = 'Lihat rincian'
    toggle.setAttribute('aria-expanded', 'false')
    toggle.addEventListener('click', (event) => {
      event.stopPropagation()
      toggleMutationRow(row)
    })

    const reorder = row.querySelector('.reorder')
    if (reorder) {
      row.insertBefore(summary, reorder)
      row.insertBefore(toggle, reorder)
    } else {
      row.append(summary, toggle)
    }
  })
}

function enhancePhysicalDateField() {
  const salePanel = document.querySelector<HTMLElement>('.sale-form-panel')
  const formGrid = salePanel?.querySelector<HTMLElement>('.form-grid.two')
  if (!formGrid || formGrid.querySelector('.physical-date-field')) return

  formGrid.classList.add('has-physical-date')
  const field = document.createElement('label')
  field.className = 'field physical-date-field'

  const caption = document.createElement('span')
  caption.textContent = 'Tanggal & jam transaksi fisik'

  const input = document.createElement('input')
  input.type = 'datetime-local'
  input.className = 'physical-date-input'
  input.value = sessionStorage.getItem(physicalDateStorageKey) || localDateTimeValue()
  input.addEventListener('change', () => sessionStorage.setItem(physicalDateStorageKey, input.value))

  const helper = document.createElement('small')
  helper.className = 'physical-date-helper'
  helper.textContent = 'Kalau telat input, isi waktu kejadian sebenarnya. Waktu input sistem tetap direkam terpisah untuk audit.'

  field.append(caption, input, helper)
  formGrid.append(field)
}

function enhancePage() {
  enhanceMutationRows()
  enhancePhysicalDateField()
}

document.addEventListener('click', (event) => {
  const target = event.target as Element | null
  if (!target) return
  const row = target.closest('.mutation-row.mutation-collapsible')
  if (!row) return
  if (target.closest('button, input, select, textarea, label, a, .multi-filter, .drag-grip, .reorder')) return
  toggleMutationRow(row)
})

document.addEventListener('keydown', (event) => {
  if (event.key !== 'Enter' && event.key !== ' ') return
  const target = event.target as Element | null
  const row = target?.closest('.mutation-row.mutation-collapsible')
  if (!row || target !== row) return
  event.preventDefault()
  toggleMutationRow(row)
})

const observer = new MutationObserver(enhancePage)
observer.observe(document.documentElement, { childList: true, subtree: true })
queueMicrotask(enhancePage)

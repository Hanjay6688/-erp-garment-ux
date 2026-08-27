const physicalDateStorageKey = 'erp.physicalTransactionAt'

function localDateTimeValue(date = new Date()) {
  const offsetMs = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16)
}

function toggleMutationRow(row: Element, force?: boolean) {
  const expanded = force ?? !row.classList.contains('is-expanded')
  const details = row.querySelector<HTMLElement>('.compact-details-grid')
  if (expanded && details && details !== row.lastElementChild) row.append(details)
  row.classList.toggle('is-expanded', expanded)
  row.setAttribute('aria-expanded', String(expanded))
  const button = row.querySelector<HTMLButtonElement>('.compact-detail-toggle')
  if (button) {
    button.textContent = expanded ? '▴' : '▾'
    button.setAttribute('aria-expanded', String(expanded))
    button.setAttribute('aria-label', expanded ? 'Tutup rincian mutasi' : 'Lihat rincian mutasi')
    button.title = expanded ? 'Tutup rincian' : 'Lihat rincian'
  }
}

function textOf(root: Element, selector: string, fallback = '—') {
  return root.querySelector<HTMLElement>(selector)?.textContent?.trim() || fallback
}

function makeSummaryMetric(label: string, value: string, conversion: string, className: string, valueClass = '') {
  const metric = document.createElement('span')
  metric.className = className

  const caption = document.createElement('small')
  caption.textContent = label

  const strong = document.createElement('strong')
  strong.textContent = value
  if (valueClass) strong.className = valueClass

  const converted = document.createElement('em')
  converted.textContent = conversion

  metric.append(caption, strong, converted)
  return metric
}

function enhanceMutationRows() {
  document.querySelectorAll<HTMLElement>('.mutation-row').forEach((row) => {
    if (row.dataset.compactReady === 'true') {
      row.classList.add('mutation-collapsible')
      const details = row.querySelector<HTMLElement>('.compact-details-grid')
      if (details && details !== row.lastElementChild) row.append(details)
      return
    }
    row.dataset.compactReady = 'true'
    row.classList.add('mutation-collapsible')
    row.setAttribute('role', 'button')
    row.setAttribute('tabindex', '0')
    row.setAttribute('aria-expanded', 'false')

    const brand = textOf(row, '.mutation-brand')
    const sku = textOf(row, '.mutation-sku-row b')
    const description = textOf(row, '.mutation-sku-row span', '')
    const movementType = textOf(row, '.type-pill')
    const referenceLine = textOf(row, '.mutation-main > p', '')
    const reference = referenceLine.split('·')[0]?.trim() || 'Tanpa referensi'
    const movementDate = textOf(row, '.mutation-main > small', '')

    const openingValue = textOf(row, '.mutation-total .total-book-step:not(.change):not(.closing) strong')
    const openingConversion = textOf(row, '.mutation-total .total-book-step:not(.change):not(.closing) small', '')
    const changeValue = textOf(row, '.mutation-total .total-book-step.change strong')
    const changeConversion = textOf(row, '.mutation-total .total-book-step.change small', '')
    const closingValue = textOf(row, '.mutation-total .total-book-step.closing strong')
    const closingConversion = textOf(row, '.mutation-total .total-book-step.closing small', '')
    const changeSource = row.querySelector<HTMLElement>('.mutation-total .total-book-step.change strong')
    const changeTone = changeSource?.classList.contains('neg') ? 'neg' : changeSource?.classList.contains('pos') ? 'pos' : ''

    const identity = document.createElement('div')
    identity.className = 'compact-identity'
    const brandNode = document.createElement('strong')
    brandNode.textContent = brand
    const skuNode = document.createElement('b')
    skuNode.textContent = sku
    const descriptionNode = document.createElement('small')
    descriptionNode.textContent = description
    identity.append(brandNode, skuNode, descriptionNode)

    const transaction = document.createElement('div')
    transaction.className = 'compact-transaction'
    const typeNode = document.createElement('span')
    typeNode.className = 'type-pill'
    typeNode.textContent = movementType
    const refNode = document.createElement('strong')
    refNode.textContent = reference
    const dateNode = document.createElement('small')
    dateNode.textContent = movementDate
    transaction.append(typeNode, refNode, dateNode)

    const summary = document.createElement('div')
    summary.className = 'compact-book-summary'
    summary.append(
      makeSummaryMetric('Saldo awal', openingValue, openingConversion, 'summary-opening'),
      makeSummaryMetric('Mutasi', changeValue, changeConversion, 'summary-change', changeTone),
      makeSummaryMetric('Saldo akhir', closingValue, closingConversion, 'summary-closing'),
    )

    const details = document.createElement('div')
    details.className = 'compact-details-grid'
    row.querySelectorAll<HTMLElement>('.mutation-delta .size-book-flow').forEach((card) => {
      details.append(card.cloneNode(true))
    })
    const totalSource = row.querySelector<HTMLElement>('.mutation-total')
    if (totalSource) {
      const totalCard = totalSource.cloneNode(true) as HTMLElement
      totalCard.classList.remove('mutation-total')
      totalCard.classList.add('compact-total-card')
      details.append(totalCard)
    }

    const toggle = document.createElement('button')
    toggle.type = 'button'
    toggle.className = 'compact-detail-toggle'
    toggle.textContent = '▾'
    toggle.setAttribute('aria-expanded', 'false')
    toggle.setAttribute('aria-label', 'Lihat rincian mutasi')
    toggle.title = 'Lihat rincian'
    toggle.addEventListener('click', (event) => {
      event.stopPropagation()
      toggleMutationRow(row)
    })

    const reorder = row.querySelector('.reorder')
    if (reorder) {
      row.insertBefore(identity, reorder)
      row.insertBefore(transaction, reorder)
      row.insertBefore(summary, reorder)
      row.insertBefore(toggle, reorder)
      row.append(details)
    } else {
      row.append(identity, transaction, summary, toggle, details)
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

document.addEventListener('dragstart', (event) => {
  const target = event.target as Element | null
  const row = target?.closest('.mutation-row.mutation-collapsible')
  if (!row) return
  toggleMutationRow(row, false)
}, true)

const observer = new MutationObserver(enhancePage)
observer.observe(document.documentElement, { childList: true, subtree: true })
queueMicrotask(enhancePage)

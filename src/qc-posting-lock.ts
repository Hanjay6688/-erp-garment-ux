const lockedButtonText = 'Posting live dikunci'
const lockedNote = 'Mode aman · posting QC dikunci sampai flow Procurement, Mandor/WIP, dan Akuntansi siap.'

function applyQcPostingLock() {
  const root = document.querySelector<HTMLElement>('.qc-prototype-root')
  if (!root) return

  const button = document.querySelector<HTMLButtonElement>('[data-live-button], [data-qc-simulate]')
  if (button) {
    if (!button.disabled) button.disabled = true
    if (button.textContent !== lockedButtonText) button.textContent = lockedButtonText
    button.dataset.postingLocked = 'true'
    button.title = 'Posting QC sementara dikunci agar stok/HPP tidak bergerak sebelum flow upstream selesai.'
  }

  const note = root.querySelector<HTMLElement>('.qc-prototype-note')
  if (note && note.textContent !== lockedNote) note.textContent = lockedNote

  const status = root.querySelector<HTMLElement>('[data-qc-live-status]')
  if (status) {
    const title = status.querySelector('strong')?.textContent
    if (title !== 'MODE AMAN · READ ONLY') {
      status.className = 'qc-live-status warn'
      status.innerHTML = '<span class="qc-live-dot"></span><div><strong>MODE AMAN · READ ONLY</strong><small>Backend tetap tersambung untuk baca konteks. Posting stok QC sengaja dikunci.</small></div>'
    }
  }

  const authPanel = document.querySelector<HTMLElement>('[data-qc-live-auth]')
  if (authPanel && !authPanel.hidden) authPanel.hidden = true
}

const lockObserver = new MutationObserver(applyQcPostingLock)
lockObserver.observe(document.documentElement, { childList: true, subtree: true })
queueMicrotask(applyQcPostingLock)

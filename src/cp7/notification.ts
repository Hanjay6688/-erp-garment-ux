import type { ChannelReadiness } from './notificationContract'
import type { ShellView } from './workspace'

export const channelReadiness: ChannelReadiness = Object.freeze({
  contract: 'READY', local_sink: 'NOT_RUN', provider: 'NOT_SELECTED',
  authorized_test: 'NOT_RUN', delivery: 'NOT_RUN', live_enabled: false,
})

// Formatting only. A rendered preview is not an outbox, send attempt or receipt.
export function previewWhatsApp(view: ShellView) {
  return view.report ? `PRATINJAU LOKAL · TIDAK DIKIRIM\n\n${view.report}` : ''
}

export function sendWhatsApp() {
  return { ok: false, code: 'DELIVERY_DISABLED', message: 'Provider, penerima dan pengiriman belum diaktifkan.' } as const
}

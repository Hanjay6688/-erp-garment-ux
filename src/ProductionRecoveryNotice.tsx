import type { useProductionMutation } from './useProductionMutation'

export default function ProductionRecoveryNotice({ recovery, onReconcile, className, noticeText, messageText, reconcileLabel='Reconcile transaksi' }: {
  recovery: ReturnType<typeof useProductionMutation>; onReconcile: () => Promise<boolean>; className: string
  noticeText?: string; messageText?: string; reconcileLabel?: string
}) {
  const message = messageText || recovery.error || recovery.blockReason
  return <>
    {message ? <div className={className} role="alert"><span>{message}</span>{recovery.pending && !recovery.corruptedEnvelope
      ? <button type="button" disabled={recovery.busy} onClick={() => void onReconcile()}>{reconcileLabel}</button> : null}</div> : null}
    {recovery.notice ? <p role="status">{noticeText || recovery.notice}</p> : null}
  </>
}

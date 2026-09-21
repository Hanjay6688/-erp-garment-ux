import type { useProductionMutation } from './useProductionMutation'

export default function ProductionRecoveryNotice({ recovery, onReconcile, className }: {
  recovery: ReturnType<typeof useProductionMutation>; onReconcile: () => Promise<boolean>; className: string
}) {
  const message = recovery.error || recovery.blockReason
  return <>
    {message ? <div className={className} role="alert"><span>{message}</span>{recovery.pending && !recovery.corruptedEnvelope
      ? <button type="button" disabled={recovery.busy} onClick={() => void onReconcile()}>Reconcile transaksi</button> : null}</div> : null}
    {recovery.notice ? <p role="status">{recovery.notice}</p> : null}
  </>
}

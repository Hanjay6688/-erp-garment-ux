import { useCallback, useEffect, useSyncExternalStore } from 'react'
import { hasProductionPending, observeProductionRecovery, readProductionRecovery } from './productionRecovery'

export const financialRecoveryMessage = 'Ada transaksi yang belum dipastikan atau catatan pemulihan perlu diperiksa. Selesaikan pemulihan di halaman transaksi terkait sebelum memuat angka keuangan lagi.'

export function financialRecoveryBlocked(scope: string): boolean {
  const recovery = readProductionRecovery(scope)
  return recovery.corrupted || hasProductionPending(recovery)
}

export function useFinancialRecoveryGate(scope: string, retire: () => void): boolean {
  const snapshot = useCallback(() => financialRecoveryBlocked(scope), [scope])
  const subscribe = useCallback((changed: () => void) => observeProductionRecovery(scope, () => {
    // Invalidate the read generation even if recovery clears before its reply.
    if (financialRecoveryBlocked(scope)) retire()
    changed()
  }), [scope, retire])
  const blocked = useSyncExternalStore(subscribe, snapshot, snapshot)
  useEffect(() => { if (blocked) retire() }, [blocked, retire])
  return blocked
}

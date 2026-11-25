import { laundryVendorNames } from './sewingModel'
import type { SupplierGroup } from './supplierInvoices'

export const partnerStorageKey = 'erp.demo.partner-master.v1'
export const standardFabricSupplier = 'Sinaran'
export const standardAccessorySupplier = 'Mitra Aksesori'
const partnerType = { FABRIC: 'Supplier Kain', ACCESSORY: 'Supplier Aksesori', LAUNDRY: 'Vendor Laundry' }
type MasterPartner = { name: string; active: boolean; values: { partnerType?: string } }

export function payablePartnerNames(group: SupplierGroup | 'LAUNDRY'): string[] {
  const saved = sessionStorage.getItem(partnerStorageKey)
  if (saved) {
    const partners: MasterPartner[] = JSON.parse(saved)
    return partners.filter(row => row.active && row.values.partnerType === partnerType[group]).map(row => row.name)
  }
  if (group === 'LAUNDRY') return laundryVendorNames
  return group === 'FABRIC' ? [standardFabricSupplier] : [standardAccessorySupplier]
}

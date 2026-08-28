export type CashAccount = {
  code: string
  name: string
  kind: 'CASH' | 'BANK' | 'EWALLET' | 'OTHER'
  balance: number
  inflow: number
  outflow: number
  reconciledAt: string
}

export type CashMovement = {
  date: string
  number: string
  source: 'CUSTOMER_PAYMENT' | 'SUPPLIER_PAYMENT' | 'VENDOR_PAYMENT' | 'PAYROLL_PAYMENT' | 'MISC_FINANCE'
  account: string
  counterparty: string
  description: string
  amount: number
  status: 'POSTED' | 'REVERSED'
}

export type Payable = {
  number: string
  party: string
  kind: 'MATERIAL_GRNI' | 'MATERIAL_AP' | 'LAUNDRY_AP'
  economicDate: string
  receivedDate: string
  dueDate: string
  amount: number
  paid: number
  status: 'WAITING_INVOICE' | 'OPEN' | 'PARTIAL' | 'PAID' | 'OVERDUE'
  costState: 'ESTIMATED' | 'ACTUAL' | 'RECALC_PENDING'
  reference: string
}

export type Receivable = {
  invoice: string
  customer: string
  invoiceDate: string
  dueDate: string
  gross: number
  returns: number
  paid: number
  status: 'OPEN' | 'PARTIAL' | 'OVERDUE'
}

export type PayrollNote = {
  number: string
  contractor: string
  period: string
  status: 'DRAFT' | 'CALCULATED' | 'REVIEW' | 'APPROVED' | 'PAID' | 'REVERSED'
  workQty: number
  labor: number
  attendance: number
  reimbursement: number
  deduction: number
  netPayable: number
  eligibleLines: number
  paymentDate: string
}

export type JournalEntry = {
  number: string
  economicDate: string
  glDate: string
  source: string
  description: string
  debit: number
  credit: number
  status: 'POSTED' | 'REVERSED'
  shifted: boolean
  lines: Array<{ account: string; description: string; debit: number; credit: number }>
}

export const cashAccounts: CashAccount[] = [
  { code:'CASH-MAIN', name:'Kas Utama', kind:'CASH', balance:84_600_000, inflow:68_420_000, outflow:51_870_000, reconciledAt:'28 Agu 2026 · 09:12' },
  { code:'BANK-BCA', name:'BCA Operasional', kind:'BANK', balance:146_250_000, inflow:214_300_000, outflow:178_050_000, reconciledAt:'28 Agu 2026 · 08:55' },
  { code:'BANK-MDR', name:'Mandiri Payroll', kind:'BANK', balance:53_750_000, inflow:72_000_000, outflow:64_800_000, reconciledAt:'27 Agu 2026 · 17:40' },
]

export const cashMovements: CashMovement[] = [
  { date:'28 Agu · 09:18', number:'PAY-CUST-0188', source:'CUSTOMER_PAYMENT', account:'BCA Operasional', counterparty:'Toko Maju Jaya', description:'Pembayaran sebagian INV-JUAL-0241', amount:2_000_000, status:'POSTED' },
  { date:'28 Agu · 08:46', number:'PAY-SUP-0107', source:'SUPPLIER_PAYMENT', account:'BCA Operasional', counterparty:'CV Sinar Textile', description:'Pelunasan BELI-KAIN-0096', amount:-18_750_000, status:'POSTED' },
  { date:'27 Agu · 16:32', number:'PAY-MANDOR-0086', source:'PAYROLL_PAYMENT', account:'Mandiri Payroll', counterparty:'Mandor Dedi', description:'Nota payroll 19–25 Agu', amount:-8_250_000, status:'POSTED' },
  { date:'27 Agu · 14:25', number:'MISC-EXP-0031', source:'MISC_FINANCE', account:'Kas Utama', counterparty:'Toko ATK Jaya', description:'Pengeluaran lain-lain · alat tulis kantor', amount:-485_000, status:'POSTED' },
  { date:'27 Agu · 11:08', number:'PAY-CUST-0187', source:'CUSTOMER_PAYMENT', account:'Kas Utama', counterparty:'Sentra Denim', description:'Pembayaran INV-JUAL-0239', amount:5_730_000, status:'POSTED' },
  { date:'26 Agu · 15:40', number:'PAY-LDY-0048', source:'VENDOR_PAYMENT', account:'BCA Operasional', counterparty:'Laundry Tirta', description:'Pembayaran sebagian INV-LDY-0081', amount:-6_400_000, status:'POSTED' },
]

export const payables: Payable[] = [
  { number:'GRNI-0098', party:'CV Sinar Textile', kind:'MATERIAL_GRNI', economicDate:'26 Agu 2026', receivedDate:'26 Agu 2026', dueDate:'—', amount:32_750_000, paid:0, status:'WAITING_INVOICE', costState:'ESTIMATED', reference:'BELI-KAIN-0098' },
  { number:'INV-ST-8821', party:'CV Sinar Textile', kind:'MATERIAL_AP', economicDate:'08 Mei 2026', receivedDate:'27 Agu 2026', dueDate:'06 Jun 2026', amount:46_850_000, paid:20_000_000, status:'OVERDUE', costState:'RECALC_PENDING', reference:'BELI-KAIN-0071 · 0078' },
  { number:'INV-BTN-229', party:'PT Kancing Nusantara', kind:'MATERIAL_AP', economicDate:'21 Agu 2026', receivedDate:'25 Agu 2026', dueDate:'20 Sep 2026', amount:12_430_000, paid:0, status:'OPEN', costState:'ACTUAL', reference:'BELI-ACC-0042' },
  { number:'INV-LDY-0081', party:'Laundry Tirta', kind:'LAUNDRY_AP', economicDate:'18 Agu 2026', receivedDate:'24 Agu 2026', dueDate:'17 Sep 2026', amount:14_880_000, paid:6_400_000, status:'PARTIAL', costState:'ACTUAL', reference:'RCV-LDY-0141 · 0144' },
  { number:'INV-LDY-0078', party:'Bersih Denim Wash', kind:'LAUNDRY_AP', economicDate:'12 Agu 2026', receivedDate:'20 Agu 2026', dueDate:'11 Sep 2026', amount:9_720_000, paid:9_720_000, status:'PAID', costState:'ACTUAL', reference:'RCV-LDY-0132' },
]

export const receivables: Receivable[] = [
  { invoice:'INV-JUAL-0241', customer:'Toko Maju Jaya', invoiceDate:'27 Agu 2026', dueDate:'26 Sep 2026', gross:7_830_000, returns:180_000, paid:4_820_000, status:'PARTIAL' },
  { invoice:'INV-JUAL-0239', customer:'Sentra Denim', invoiceDate:'27 Agu 2026', dueDate:'27 Agu 2026', gross:5_730_000, returns:0, paid:0, status:'OVERDUE' },
  { invoice:'INV-JUAL-0237', customer:'Nusantara Fashion', invoiceDate:'22 Agu 2026', dueDate:'21 Sep 2026', gross:12_640_000, returns:860_000, paid:8_000_000, status:'PARTIAL' },
  { invoice:'INV-JUAL-0232', customer:'Toko Maju Jaya', invoiceDate:'14 Agu 2026', dueDate:'14 Agu 2026', gross:4_920_000, returns:0, paid:3_000_000, status:'OVERDUE' },
]

export const payrollNotes: PayrollNote[] = [
  { number:'PAY-MANDOR-0089', contractor:'Mandor Budi', period:'26–28 Agu 2026', status:'DRAFT', workQty:486, labor:8_420_000, attendance:0, reimbursement:1_240_000, deduction:860_000, netPayable:8_800_000, eligibleLines:14, paymentDate:'28 Agu 2026' },
  { number:'PAY-MANDOR-0088', contractor:'Mandor Rian', period:'19–25 Agu 2026', status:'REVIEW', workQty:612, labor:10_780_000, attendance:720_000, reimbursement:1_680_000, deduction:2_340_000, netPayable:10_840_000, eligibleLines:3, paymentDate:'28 Agu 2026' },
  { number:'PAY-MANDOR-0087', contractor:'Mandor Dedi', period:'19–25 Agu 2026', status:'APPROVED', workQty:525, labor:9_150_000, attendance:0, reimbursement:980_000, deduction:1_430_000, netPayable:8_700_000, eligibleLines:0, paymentDate:'28 Agu 2026' },
  { number:'PAY-MANDOR-0086', contractor:'Mandor Dedi', period:'12–18 Agu 2026', status:'PAID', workQty:498, labor:8_860_000, attendance:0, reimbursement:840_000, deduction:1_450_000, netPayable:8_250_000, eligibleLines:0, paymentDate:'27 Agu 2026' },
]

export const journals: JournalEntry[] = [
  { number:'JRN-202608280918-01', economicDate:'28 Agu 2026', glDate:'28 Agu 2026', source:'CUSTOMER_PAYMENT', description:'Pembayaran pelanggan PAY-CUST-0188', debit:2_000_000, credit:2_000_000, status:'POSTED', shifted:false, lines:[{account:'1102 · BCA Operasional',description:'Uang masuk',debit:2_000_000,credit:0},{account:'1201 · Piutang pelanggan',description:'Pelunasan sebagian',debit:0,credit:2_000_000}] },
  { number:'JRN-202608271425-31', economicDate:'27 Agu 2026', glDate:'27 Agu 2026', source:'MISC_FINANCE', description:'Alat tulis kantor', debit:485_000, credit:485_000, status:'POSTED', shifted:false, lines:[{account:'6909 · Pengeluaran lain-lain',description:'ATK',debit:485_000,credit:0},{account:'1101 · Kas Utama',description:'Kas keluar',debit:0,credit:485_000}] },
  { number:'JRN-202608271012-82', economicDate:'08 Mei 2026', glDate:'27 Agu 2026', source:'MATERIAL_SUPPLIER_INVOICE', description:'Invoice terlambat CV Sinar Textile', debit:46_850_000, credit:46_850_000, status:'POSTED', shifted:true, lines:[{account:'2102 · GRNI bahan',description:'Clear estimasi receipt',debit:32_000_000,credit:0},{account:'1301 · Persediaan/WIP/COGS bridge',description:'Recost selisih',debit:14_850_000,credit:0},{account:'2101 · Hutang supplier',description:'AP final',debit:0,credit:46_850_000}] },
  { number:'JRN-202608261540-48', economicDate:'26 Agu 2026', glDate:'26 Agu 2026', source:'VENDOR_PAYMENT', description:'Pembayaran Laundry Tirta', debit:6_400_000, credit:6_400_000, status:'REVERSED', shifted:false, lines:[{account:'2103 · Hutang vendor',description:'Kurangi AP',debit:6_400_000,credit:0},{account:'1102 · BCA Operasional',description:'Uang keluar',debit:0,credit:6_400_000}] },
]

export const closeChecks = [
  { label:'Jurnal tidak seimbang', count:0, severity:'CLEAR' as const },
  { label:'Draft transaksi melewati periode', count:4, severity:'WARNING' as const },
  { label:'GRNI belum jadi invoice > 30 hari', count:3, severity:'WARNING' as const },
  { label:'Cost recalc masih antre', count:1, severity:'BLOCK' as const },
  { label:'Kas/bank belum direkonsiliasi', count:1, severity:'WARNING' as const },
]

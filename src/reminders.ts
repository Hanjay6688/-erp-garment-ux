export type ReminderPriority = 'URGENT' | 'NORMAL' | 'LOW'
export type ReminderStatus = 'OPEN' | 'DONE'

export type ReminderItem = {
  id: string
  title: string
  note: string
  dueAt: string
  priority: ReminderPriority
  status: ReminderStatus
  module: string
  createdAt: string
  completedAt?: string
}

export const initialReminders: ReminderItem[] = [
  {
    id: 'RMD-260830-001',
    title: 'Tanyakan 64 pcs yang belum kembali',
    note: 'Laundry Intan · POT-260826-041 · pastikan jadwal kirim susulan.',
    dueAt: '2026-08-31T09:00',
    priority: 'URGENT',
    status: 'OPEN',
    module: 'Laundry',
    createdAt: '30 Agu 2026 · 19:12',
  },
  {
    id: 'RMD-260830-002',
    title: 'Cocokkan kasbon kain Sinaran',
    note: 'Tiga receipt masih memakai harga benchmark dan belum menjadi invoice final.',
    dueAt: '2026-09-01T10:30',
    priority: 'NORMAL',
    status: 'OPEN',
    module: 'Hutang Supplier',
    createdAt: '30 Agu 2026 · 19:18',
  },
  {
    id: 'RMD-260829-008',
    title: 'Review pembagian POT-260827-039',
    note: 'Mandor Afui sudah dikonfirmasi dan detail roll sudah sesuai.',
    dueAt: '2026-08-30T08:00',
    priority: 'LOW',
    status: 'DONE',
    module: 'Bagi Potongan',
    createdAt: '29 Agu 2026 · 16:45',
    completedAt: '30 Agu 2026 · 08:14',
  },
]

export const reminderPriorityLabel: Record<ReminderPriority, string> = {
  URGENT: 'Penting',
  NORMAL: 'Normal',
  LOW: 'Santai',
}

export const reminderDueLabel = (dueAt: string) => new Intl.DateTimeFormat('id-ID', {
  day: 'numeric',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
}).format(new Date(dueAt))

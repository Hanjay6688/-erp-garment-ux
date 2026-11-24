import {
  ArrowLeft,
  ArrowRight,
  Boxes,
  CalendarDays,
  Check,
  ChevronDown,
  ChevronUp,
  CircleDollarSign,
  Database,
  Factory,
  FileText,
  GripVertical,
  History,
  Layers3,
  LayoutDashboard,
  Link2,
  ListFilter,
  Menu,
  Package,
  Plus,
  ReceiptText,
  RotateCcw,
  Ruler,
  Scissors,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Trash2,
  UserRound,
  WalletCards,
  Warehouse,
  X,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export function Icon({ name }: { name: string }) {
  const icons: Record<string, LucideIcon> = {
    dashboard: LayoutDashboard, Produksi: Factory, Gudang: Warehouse, Penjualan: ReceiptText,
    Keuangan: WalletCards, 'Master Data': Database, audit: ShieldCheck, search: Search,
    back: ArrowLeft, stock: Layers3, check: Check, menu: Menu, up: ChevronUp, down: ChevronDown,
    reset: RotateCcw, filter: SlidersHorizontal, calendar: CalendarDays, user: UserRound,
    arrow: ArrowRight, drag: GripVertical, close: X, chevron: ChevronDown, brand: Scissors,
    product: Package, list: ListFilter, boxes: Boxes, cost: CircleDollarSign,
    document: FileText, history: History, link: Link2, plus: Plus, ruler: Ruler,
    trash: Trash2,
  }
  const Glyph = icons[name] ?? Package
  return <Glyph className="icon" strokeWidth={1.8} aria-hidden="true" />
}

import { createClient } from '@supabase/supabase-js'

const supabaseUrl = 'https://vlxdhpkjeevubjxexnfo.supabase.co'
const supabasePublishableKey = 'sb_publishable_OngVncWBmyTYT5oP8eXvJA_NtxlM_r1'

export const supabase = createClient(supabaseUrl, supabasePublishableKey, {
  db: { schema: 'erp' },
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
})

export type QcLiveSource = {
  po_id: string
  po_number: string
  model_id: string
  model_code: string
  model_name: string
  cutting_group_id: string
  group_number: string
  executor_name: string
  source_laundry_receipt_line_id: string | null
  source_label: string
  available_qty_pcs: number
  earliest_qc_at: string
}

export type QcLiveProduct = {
  product_id: string
  sku: string
  product_name: string
  color_name: string
  model_id: string
  model_code: string
  model_name: string
  brand_name: string
  size_code: string
  sort_order: number
}

export type QcLiveLocation = {
  id: string
  location_code: string
  location_name: string
}

export type QcEntryContext = {
  role: string | null
  sources: QcLiveSource[]
  products: QcLiveProduct[]
  locations: QcLiveLocation[]
}

export async function getQcEntryContext() {
  const { data, error } = await supabase.schema('erp').rpc('get_qc_entry_context')
  if (error) throw error
  return data as QcEntryContext
}

export async function sendInternalMagicLink(email: string) {
  const redirectTo = `${window.location.origin}${window.location.pathname}`
  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: {
      shouldCreateUser: false,
      emailRedirectTo: redirectTo,
    },
  })
  if (error) throw error
}

export type CreateQcPayload = {
  p_request_id: string
  p_po_id: string
  p_destination_location_id: string
  p_physical_at: string
  p_notes: string | null
  p_items: Array<{
    cutting_group_id: string
    source_laundry_receipt_line_id: string | null
    final_product_id: string
    qty_good_pcs: number
    qty_bs_pcs: number
    qty_rework_pcs: number
    notes: string | null
  }>
}

export async function createAndPostQc(payload: CreateQcPayload) {
  const { data, error } = await supabase.schema('erp').rpc('create_and_post_qc', payload)
  if (error) throw error
  return data as {
    qc_id: string
    inspection_number: string
    status: string
    idempotent_replay: boolean
  }
}

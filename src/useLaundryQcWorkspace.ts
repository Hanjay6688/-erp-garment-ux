import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { normalizeClientError } from './lib/clientError'
import { getUatSupabaseClient } from './lib/supabase'
import { useProductionMutation } from './useProductionMutation'
import type { ProductionEnvelope } from './productionRecovery'
import {
  parseFinalSkuProductSearch, parseLaundryBsProductSearch, parseLaundryQcWorkspace,
  type Cp6LaundryBsProductSearchPage, type Cp6ProductSearchPage,
  type LaundryQcAction, type LaundryQcScope, type LaundryQcWorkspace,
} from './laundryQcModel'
import type { Json } from './types/database.preconnect'

function validateCommitted(data: unknown, envelope: ProductionEnvelope) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('Respons CP6 tidak valid')
  const value = data as Record<string, unknown>
  if (value.contract_version !== 'CP6_V2620' || value.committed !== true
    || value.action !== envelope.action || value.client_request_id !== envelope.id) throw new Error('UUID/action CP6 tidak cocok')
}

export function useLaundryQcWorkspace(scope: LaundryQcScope) {
  const { runtime } = useAuth()
  if (!isConnectedRuntime(runtime)) throw new Error('Laundry/QC memerlukan sesi connected.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const mutation = useProductionMutation('LAUNDRY_QC')
  const { beginRead, finishRead, run, reconcile: reconcileMutation } = mutation
  const [workspace, setWorkspace] = useState<LaundryQcWorkspace | null>(null)
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [committedRefreshRequired, setCommittedRefreshRequired] = useState(false)
  const requestRef = useRef(0)
  const queryRef = useRef(query)
  queryRef.current = query
  const load = useCallback(async (nextQuery = queryRef.current) => {
    const ticket = beginRead()
    const request = ++requestRef.current
    setLoading(true); setLoadError('')
    try {
      const { data, error } = await client.rpc('erp_get_laundry_qc_workspace_v1', { p_scope: scope, p_query: nextQuery.trim() || null })
      if (request !== requestRef.current) return false
      if (error) throw error
      const parsed = parseLaundryQcWorkspace(data)
      if (parsed.scope !== scope) throw new Error('Respons workspace tidak cocok dengan halaman yang diminta.')
      setWorkspace(parsed)
      return finishRead(ticket)
    } catch (error) {
      if (request === requestRef.current) setLoadError(normalizeClientError(error).message)
      return false
    } finally { if (request === requestRef.current) setLoading(false) }
  }, [beginRead, client, finishRead, scope])
  const sendExact = useCallback((envelope: ProductionEnvelope) => client.rpc('erp_save_laundry_qc_action_v1', {
    p_action: envelope.action, p_payload: envelope.payload, p_client_request_id: envelope.id, p_expected_version: envelope.expectedVersion,
  }), [client])
  const searchFinalSkuProducts = useCallback(async (
    sourceBatchSizeLineId: string,
    physicalAt: string,
    productQuery: string,
    afterSortKey: string | null = null,
  ): Promise<Cp6ProductSearchPage> => {
    const { data, error: searchError } = await client.rpc('erp_search_final_sku_products_v1', {
      p_source_laundry_receipt_batch_size_line_id: sourceBatchSizeLineId,
      p_physical_at: physicalAt,
      p_query: productQuery.trim() || null,
      p_after_sort_key: afterSortKey,
      p_limit: 50,
    })
    if (searchError) throw searchError
    const page = parseFinalSkuProductSearch(data)
    if (page.source_laundry_receipt_batch_size_line_id !== sourceBatchSizeLineId
      || Date.parse(page.physical_at) !== Date.parse(physicalAt)
      || page.page_limit !== 50) {
      throw new Error('Respons pencarian Final SKU tidak cocok dengan sumber/waktu yang diminta.')
    }
    return page
  }, [client])

  const searchLaundryBsProducts = useCallback(async (
    deliveryBatchSizeLineId: string,
    physicalAt: string,
    productQuery: string,
    afterSortKey: string | null = null,
  ): Promise<Cp6LaundryBsProductSearchPage> => {
    const { data, error: searchError } = await client.rpc('erp_search_laundry_bs_products_v1', {
      p_delivery_batch_size_line_id: deliveryBatchSizeLineId,
      p_physical_at: physicalAt,
      p_query: productQuery.trim() || null,
      p_after_sort_key: afterSortKey,
      p_limit: 50,
    })
    if (searchError) throw searchError
    const page = parseLaundryBsProductSearch(data)
    if (page.source_delivery_batch_size_line_id !== deliveryBatchSizeLineId
      || Date.parse(page.physical_at) !== Date.parse(physicalAt)
      || page.page_limit !== 50) {
      throw new Error('Respons pencarian SKU Laundry-BS tidak cocok dengan sumber/waktu yang diminta.')
    }
    return page
  }, [client])


  const reconcile = useCallback(() => reconcileMutation({
    send: sendExact, validate: validateCommitted, reload: load,
    retire: () => setCommittedRefreshRequired(true),
  }), [load, reconcileMutation, sendExact])
  const runAction = useCallback((action: LaundryQcAction, payload: Json, expectedVersion: number | null, retireCommittedForm: () => void) => {
    if (committedRefreshRequired) return Promise.resolve(false)
    return run(action, payload, expectedVersion, {
      send: sendExact, validate: validateCommitted, reload: load,
      retire: () => { setCommittedRefreshRequired(true); retireCommittedForm() },
    })
  }, [committedRefreshRequired, load, run, sendExact])
  useEffect(() => {
    if (mutation.corruptedEnvelope) return
    if (mutation.pending) void reconcile()
    else void load()
    return () => { requestRef.current += 1 }
  }, [mutation.scope, scope]) // eslint-disable-line react-hooks/exhaustive-deps
  const acknowledgeCommittedFormRetired = useCallback((sequence: number) => {
    if (sequence <= 0 || sequence !== mutation.committedSequence || mutation.writerLocked) return false
    setCommittedRefreshRequired(false)
    return true
  }, [mutation.committedSequence, mutation.writerLocked])
  const search = (next: string) => { setQuery(next); void load(next) }
  return {
    workspace, query, loading, busy: mutation.busy,
    error: mutation.error || (mutation.corruptedEnvelope ? mutation.blockReason : loadError || mutation.blockReason), notice: mutation.notice,
    pending: mutation.pending, corruptedEnvelope: mutation.corruptedEnvelope,
    workspaceStale: mutation.workspaceStale, externalMutationBlocked: mutation.externalMutationBlocked,
    committedRefreshRequired, committedSequence: mutation.committedSequence,
    writerLocked: mutation.writerLocked || committedRefreshRequired,
    search, load, runAction, reconcile, searchFinalSkuProducts, searchLaundryBsProducts, acknowledgeCommittedFormRetired,
  }
}

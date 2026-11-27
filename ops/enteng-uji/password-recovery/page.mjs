import { createClient } from '@supabase/supabase-js'

const site = 'https://erp-garment-ux-enteng-uji-build-check.zrpf6sbtjb.workers.dev'
const project = 'https://jxzlajjuuaexiwfjseav.supabase.co'
const path = '/auth/atur-sandi/'
const authUrl = project + '/auth/v1'
const key = __UJI_PUBLISHABLE_KEY__
const status = document.querySelector('#status')
const title = document.querySelector('#title')
const request = document.querySelector('#request')
const change = document.querySelector('#change')
const again = document.querySelector('#again')
const storageKey = 'atelier-uat-pemulihan'

function legacyStorage() {
  // Older emails require a verifier from the browser that requested them.
  const memory = new Map()
  const isVerifier = k => k.startsWith(storageKey + '-') && k.endsWith('-code-verifier')
  return {
    getItem(k) { return isVerifier(k) ? localStorage.getItem(k) : memory.get(k) ?? null },
    setItem(k, v) { if (isVerifier(k)) localStorage.setItem(k, v); else memory.set(k, v) },
    removeItem(k) { if (isVerifier(k)) localStorage.removeItem(k); else memory.delete(k) },
  }
}

function unusable(message) {
  change.reset()
  change.hidden = true
  request.hidden = true
  title.textContent = 'Tautan pemulihan'
  status.textContent = message
  again.hidden = false
}

const expired = 'Tautan ini sudah kedaluwarsa atau pernah dipakai. Gunakan email pemulihan yang paling baru.'
const incomplete = 'Tautan ini tidak lengkap. Buka tombol Reset password dari email pemulihan Enteng Uji.'

function parseCallback(url) {
  const query = url.searchParams
  const hash = new URLSearchParams(url.hash.slice(1))
  if (!url.search && !url.hash) return { kind: 'request' }
  if ([query, hash].some(p => p.has('error') || p.has('error_code'))) return { error: expired }
  if (query.has('code') && !url.hash) {
    const code = query.get('code')
    const flowId = query.get('sb_flow_id')
    if (query.getAll('code').length === 1 && /^[A-Za-z0-9_-]{16,512}$/.test(code)
      && query.getAll('sb_flow_id').length <= 1 && (flowId === null || /^[A-Za-z0-9_-]{8,64}$/.test(flowId))
      && [...query.keys()].every(k => k === 'code' || k === 'sb_flow_id')) {
      return { kind: 'legacy', code, flowId }
    }
    return { error: incomplete }
  }
  // Only the access token from the dedicated recovery callback is needed.
  // The general ERP sign-in page never processes URL credentials.
  if (!url.search && hash.getAll('type').length === 1 && hash.get('type') === 'recovery'
    && hash.getAll('access_token').length === 1) {
    const token = hash.get('access_token')
    if (token.length < 16384 && /^[\w-]+\.[\w-]+\.[\w-]+$/.test(token)) return { kind: 'email', token }
  }
  return { error: incomplete }
}

async function emailIdentity(auth, token) {
  // The fragment label is a routing hint. Authenticate the token and user with this project.
  const [identity, signed] = await Promise.all([auth.getUser(token), auth.getClaims(token)])
  const u = identity.data?.user
  const c = signed.data?.claims
  if (identity.error || signed.error || !u?.email_confirmed_at || !u.email || !c
    || c.sub !== u.id || c.iss !== authUrl || c.role !== 'authenticated') return null
  const requested = Math.floor(Date.parse(u.recovery_sent_at) / 1000)
  // GoTrue records email verification as otp in implicit flows.
  const verified = c.amr?.some(m => ['otp', 'recovery'].includes(m.method) && m.timestamp >= requested - 1)
  return verified ? u : null
}

async function userRequest(route, method, token, body) {
  const headers = { apikey: key, Authorization: 'Bearer ' + token }
  if (body) headers['Content-Type'] = 'application/json'
  return fetch(authUrl + route, {
    method, headers, body: body && JSON.stringify(body),
    credentials: 'omit', referrerPolicy: 'no-referrer', redirect: 'error', cache: 'no-store',
  })
}

async function start() {
  const url = new URL(location.href)
  const callback = parseCallback(url)
  if (url.hash || url.search) history.replaceState(null, '', url.pathname)
  if (url.origin !== site || url.pathname !== path) {
    status.textContent = 'Halaman ini hanya tersedia di Enteng Uji.'
    return
  }
  if (callback.error) return unusable(callback.error)
  const legacy = callback.kind === 'legacy'
  const { auth } = createClient(project, key, { auth: {
    storageKey, flowType: legacy ? 'pkce' : 'implicit', persistSession: legacy,
    autoRefreshToken: false, detectSessionInUrl: false, ...(legacy && { storage: legacyStorage() }),
  } })
  if (callback.kind === 'request') {
    request.hidden = false
    request.addEventListener('submit', async event => {
      event.preventDefault()
      const button = request.querySelector('button')
      if (button.disabled) return
      button.disabled = true
      try {
        const { error } = await auth.resetPasswordForEmail(request.elements.email.value.trim(), { redirectTo: site + path })
        if (error) {
          status.textContent = error.status === 429
            ? 'Supabase sedang membatasi pengiriman email. Tunggu sampai kuota tersedia lagi sebelum mengirim ulang.'
            : 'Email belum terkirim. Periksa koneksi dan coba lagi.'
          return
        }
        request.hidden = true
        title.textContent = 'Cek email lu'
        status.textContent = 'Jika email terdaftar, buka email terbaru dari Supabase dan tekan Reset password. Lu bisa membukanya di perangkat lain.'
      } catch { status.textContent = 'Email belum terkirim. Periksa koneksi dan coba lagi.' }
      finally { button.disabled = false }
    })
    return
  }
  title.textContent = 'Memeriksa tautan'
  let token = callback.token
  let user
  if (legacy) {
    const { data, error } = await auth.exchangeCodeForSession(callback.code, callback.flowId ? { flowId: callback.flowId } : undefined)
    if (error?.code === 'pkce_code_verifier_not_found') {
      return unusable('Email lama ini terikat ke browser yang meminta tautan. Minta tautan baru untuk membukanya dari perangkat lain.')
    }
    if (error || data?.redirectType !== 'recovery' || !data?.session?.access_token) return unusable(expired)
    token = data.session.access_token
    const identity = await auth.getUser(token)
    if (!identity.error && identity.data.user?.id === data.user?.id) user = identity.data.user
  } else {
    user = await emailIdentity(auth, token)
  }
  if (!user?.id || !user.email) return unusable(expired)
  const userId = user.id
  document.querySelector('#identity').textContent = user.email
  title.textContent = 'Buat sandi ERP baru'
  change.hidden = false
  change.addEventListener('submit', async event => {
    event.preventDefault()
    const button = change.querySelector('button')
    if (!token || button.disabled) return
    const password = change.elements.password.value
    if (password.length < 12 || password.length > 128 || /\s/.test(password)
      || !/[A-Z]/.test(password) || !/[a-z]/.test(password) || !/[0-9]/.test(password) || !/[^A-Za-z0-9]/.test(password)) {
      status.textContent = 'Kata sandi belum memenuhi syarat di bawah isian.'
      return
    }
    if (password !== change.elements.repeat.value) {
      status.textContent = 'Kedua kata sandi belum sama.'
      return
    }
    button.disabled = true
    try {
      const identity = await auth.getUser(token)
      if (identity.error || identity.data.user?.id !== userId) return unusable(expired)
      // Use this single verified grant. Never import a refresh token or reuse an ERP login session.
      const response = await userRequest('/user', 'PUT', token, { password })
      if (response.status === 401 || response.status === 403) return unusable(expired)
      if (!response.ok) {
        status.textContent = 'Sandi belum tersimpan. Pilih sandi baru yang memenuhi syarat.'
        return
      }
      if ((await response.json()).id !== userId) throw new Error('Unexpected user')
      const used = token
      token = null
      change.reset()
      change.hidden = true
      title.textContent = 'Sandi ERP sudah tersimpan'
      status.textContent = 'Lu sudah bisa masuk ke Enteng Uji dengan sandi yang baru.'
      await userRequest('/logout?scope=local', 'POST', used).catch(() => {})
    } catch { status.textContent = 'Belum ada konfirmasi penyimpanan. Periksa koneksi sebelum mencoba lagi.' }
    finally { button.disabled = false }
  })
}

start().catch(() => unusable('Halaman belum bisa memeriksa tautan. Periksa koneksi ke Enteng Uji.'))

import { createClient } from '@supabase/supabase-js'

const site = 'https://erp-garment-ux-enteng-uji-build-check.zrpf6sbtjb.workers.dev'
const project = 'https://jxzlajjuuaexiwfjseav.supabase.co'
const path = '/auth/atur-sandi/'
const status = document.querySelector('#status')
const request = document.querySelector('#request')
const change = document.querySelector('#change')
const memory = new Map()
const storageKey = 'atelier-uat-pemulihan'

// Only the PKCE state may cross tabs. Recovery sessions live in memory,
// isolated from the ERP operator session and from future visitors.
const isVerifier = key => key.startsWith(storageKey + '-') && key.endsWith('-code-verifier')
const storage = {
  getItem(key) { return isVerifier(key) ? localStorage.getItem(key) : memory.get(key) ?? null },
  setItem(key, value) { if (isVerifier(key)) localStorage.setItem(key, value); else memory.set(key, value) },
  removeItem(key) { if (isVerifier(key)) localStorage.removeItem(key); else memory.delete(key) },
}

async function start() {
  const url = new URL(location.href)
  const codes = url.searchParams.getAll('code')
  const invalid = Boolean(url.hash) || [...url.searchParams.keys()].some(k => k !== 'code') || codes.length > 1
  if (url.search || url.hash) history.replaceState(null, '', url.pathname)
  if (url.origin !== site || url.pathname !== path) {
    status.textContent = 'Halaman ini hanya tersedia di Enteng Uji.'
    return
  }
  const client = createClient(project, __UJI_PUBLISHABLE_KEY__, {
    auth: { storageKey, storage, flowType: 'pkce', persistSession: true, autoRefreshToken: false, detectSessionInUrl: false },
  })
  let recoveryUser = null
  let changed = false
  const retry = 'Tautan belum bisa dipakai. Minta tautan baru dan buka di browser yang sama.'
  request.addEventListener('submit', async event => {
    event.preventDefault()
    const button = request.querySelector('button')
    if (button.disabled) return
    button.disabled = true
    try {
      const { error } = await client.auth.resetPasswordForEmail(request.elements.email.value.trim(), { redirectTo: site + path })
      if (error) {
        status.textContent = error.status === 429 ? 'Terlalu banyak permintaan. Tunggu sebelum mencoba lagi.' : 'Tautan belum terkirim. Coba lagi.'
        return
      }
      request.hidden = true
      status.textContent = 'Cek kotak masuk dan folder spam. Jika email terdaftar, buka tautan dari Supabase di browser ini.'
    } catch { status.textContent = 'Tautan belum terkirim. Periksa koneksi dan coba lagi.' }
    finally { button.disabled = false }
  })
  change.addEventListener('submit', async event => {
    event.preventDefault()
    const button = change.querySelector('button')
    if (!recoveryUser || changed || button.disabled) return
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
      const { data: identity, error } = await client.auth.getUser()
      if (error || identity.user?.id !== recoveryUser) {
        change.reset()
        change.hidden = true
        request.hidden = false
        recoveryUser = null
        status.textContent = retry
        return
      }
      const update = await client.auth.updateUser({ password })
      if (update.error || update.data.user?.id !== recoveryUser) {
        status.textContent = 'Kata sandi belum tersimpan. Periksa syaratnya atau minta tautan baru.'
        return
      }
      changed = true
      change.reset()
      change.hidden = true
      recoveryUser = null
      status.textContent = 'Kata sandi ERP sudah tersimpan. Lu bisa masuk lewat tautan di bawah.'
      await client.auth.signOut({ scope: 'local' }).catch(() => {})
    } catch {
      if (!changed) status.textContent = 'Belum ada konfirmasi penyimpanan. Periksa koneksi sebelum mencoba lagi.'
    } finally { button.disabled = false }
  })
  if (invalid || (codes.length && !/^[A-Za-z0-9_-]{16,512}$/.test(codes[0]))) {
    status.textContent = retry
  } else if (codes.length) {
    try {
      const { data, error } = await client.auth.exchangeCodeForSession(codes[0])
      if (!error && data.redirectType === 'recovery' && data.session && data.user?.id) {
        recoveryUser = data.user.id
        document.querySelector('#identity').textContent = data.user.email
        change.hidden = false
        return
      }
    } catch { /* Leave the user a way to request a new link. */ }
    await client.auth.signOut({ scope: 'local' }).catch(() => {})
    status.textContent = retry
  }
  request.hidden = false
}

start().catch(() => { status.textContent = 'Halaman belum siap. Buka lagi di browser yang mengizinkan penyimpanan lokal.' })

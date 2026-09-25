export type ClientErrorCode =
  | 'AUTH_FAILED'
  | 'AUTH_REQUIRED'
  | 'FORBIDDEN'
  | 'PROFILE_API_SCHEMA_UNAVAILABLE'
  | 'NOT_FOUND'
  | 'VERSION_CONFLICT'
  | 'DATA_CONFLICT'
  | 'DUPLICATE_REQUEST'
  | 'RETRYABLE_CONFLICT'
  | 'REJECTED'
  | 'BACKEND_UNAVAILABLE'

export class ClientAppError extends Error {
  readonly code: ClientErrorCode
  readonly retryable: boolean

  constructor(code: ClientErrorCode, message: string, retryable = false) {
    super(message)
    this.name = 'ClientAppError'
    this.code = code
    this.retryable = retryable
  }
}

type ErrorLike = {
  code?: unknown
  status?: unknown
  message?: unknown
}

function errorLike(error: unknown): ErrorLike {
  return error !== null && typeof error === 'object' ? error as ErrorLike : {}
}

export function normalizeClientError(error: unknown): ClientAppError {
  if (error instanceof ClientAppError) return error

  const candidate = errorLike(error)
  const code = typeof candidate.code === 'string' ? candidate.code.toUpperCase() : ''
  const status = typeof candidate.status === 'number' ? candidate.status : Number.NaN
  const rawMessage = typeof candidate.message === 'string' ? candidate.message.toLowerCase() : ''

  if (code === 'PGRST106') {
    return new ClientAppError(
      'PROFILE_API_SCHEMA_UNAVAILABLE',
      'Facade self-profile Auth belum tersedia secara aman di Data API UAT.',
    )
  }
  if (status === 401 || code === 'PGRST301') {
    return new ClientAppError('AUTH_REQUIRED', 'Sesi berakhir. Silakan masuk ulang.')
  }
  if (status === 403 || code === '42501') {
    return new ClientAppError('FORBIDDEN', 'Akun tidak memiliki izin untuk operasi ini.')
  }
  if (code === 'PGRST116') {
    return new ClientAppError('NOT_FOUND', 'Data yang diminta tidak ditemukan.')
  }
  if (rawMessage.includes('request_uuid') || rawMessage.includes('idempot')) {
    return new ClientAppError('DUPLICATE_REQUEST', 'Identitas permintaan bertabrakan. Muat ulang status sebelum mengirim ulang.')
  }
  if (code === '23505') {
    return new ClientAppError('DATA_CONFLICT', 'Data bertabrakan dengan catatan yang sudah ada. Muat ulang dan periksa data sebelum menyimpan lagi.')
  }
  if (code === '40001' || code === '40P01') {
    return new ClientAppError('RETRYABLE_CONFLICT', 'Terjadi benturan sementara. Muat ulang sebelum mencoba lagi.', true)
  }
  if (rawMessage.includes('row_version') || rawMessage.includes('expected_version')) {
    return new ClientAppError('VERSION_CONFLICT', 'Data berubah di perangkat lain. Muat ulang sebelum menyimpan.')
  }

  // W11 (independent audit round 9): only a failure that never got an answer is "unreachable"; a refusal with a message
  // (a server rule such as CLOSE_ALREADY_CLOSED, or a page parser such as "Model produk bukan UUID valid.") is shown as is.
  const originalMessage = typeof candidate.message === 'string' ? candidate.message.trim() : ''
  if (!isUnansweredFailure(error) && originalMessage) {
    return new ClientAppError('REJECTED', originalMessage)
  }
  return new ClientAppError('BACKEND_UNAVAILABLE', 'Layanan UAT belum dapat dihubungi. Coba lagi setelah status diperiksa.', true)
}

const networkWords = ['failed to fetch', 'fetch failed', 'networkerror', 'network error', 'network request failed', 'network unavailable',
  'load failed', 'timeout', 'timed out', 'aborted', 'econnreset', 'econnrefused']

/**
 * True when the request may not have reached the server or its answer was lost (no server answer to rely on): a thrown
 * TypeError from fetch, an abort, a gateway status (502/503/504), status 0, or a network wording. The outcome of such a
 * write is unknown, so its request identity must be kept for an exact replay (M:1679, M:3819).
 */
export function isUnansweredFailure(error: unknown): boolean {
  if (error instanceof TypeError) return true
  const candidate = errorLike(error)
  if (error instanceof Error && error.name === 'AbortError') return true
  const status = typeof candidate.status === 'number' ? candidate.status : Number.NaN
  if (status === 0 || status === 502 || status === 503 || status === 504) return true
  const code = typeof candidate.code === 'string' ? candidate.code : ''
  const message = typeof candidate.message === 'string' ? candidate.message.toLowerCase() : ''
  if (!message) return true
  return !code && networkWords.some((word) => message.includes(word))
}

export function normalizeAuthError(error: unknown): ClientAppError {
  const candidate = errorLike(error)
  const code = typeof candidate.code === 'string' ? candidate.code.toLowerCase() : ''
  if (code === 'invalid_credentials' || code === 'email_not_confirmed') {
    return new ClientAppError('AUTH_FAILED', 'Email atau kata sandi tidak valid, atau akun belum dikonfirmasi.')
  }
  return normalizeClientError(error)
}

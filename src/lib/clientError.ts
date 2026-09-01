export type ClientErrorCode =
  | 'AUTH_FAILED'
  | 'AUTH_REQUIRED'
  | 'FORBIDDEN'
  | 'PROFILE_API_SCHEMA_UNAVAILABLE'
  | 'NOT_FOUND'
  | 'VERSION_CONFLICT'
  | 'DUPLICATE_REQUEST'
  | 'RETRYABLE_CONFLICT'
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
  if (code === '23505' || rawMessage.includes('request_uuid') || rawMessage.includes('idempot')) {
    return new ClientAppError('DUPLICATE_REQUEST', 'Permintaan ini sudah pernah diproses.')
  }
  if (code === '40001' || code === '40P01') {
    return new ClientAppError('RETRYABLE_CONFLICT', 'Terjadi benturan sementara. Muat ulang sebelum mencoba lagi.', true)
  }
  if (rawMessage.includes('row_version') || rawMessage.includes('expected_version')) {
    return new ClientAppError('VERSION_CONFLICT', 'Data berubah di perangkat lain. Muat ulang sebelum menyimpan.')
  }

  return new ClientAppError('BACKEND_UNAVAILABLE', 'Layanan UAT belum dapat dihubungi. Coba lagi setelah status diperiksa.', true)
}

export function normalizeAuthError(error: unknown): ClientAppError {
  const candidate = errorLike(error)
  const code = typeof candidate.code === 'string' ? candidate.code.toLowerCase() : ''
  if (code === 'invalid_credentials' || code === 'email_not_confirmed') {
    return new ClientAppError('AUTH_FAILED', 'Email atau kata sandi tidak valid, atau akun belum dikonfirmasi.')
  }
  return normalizeClientError(error)
}

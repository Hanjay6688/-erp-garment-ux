import { ClientAppError } from './clientError'

const canonicalUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

export function isRequestId(value: string) {
  return canonicalUuid.test(value)
}

export function createRequestId(randomUuid: () => string = () => globalThis.crypto.randomUUID()) {
  const requestId = randomUuid()
  if (!isRequestId(requestId)) {
    throw new ClientAppError('INVALID_REQUEST_ID', 'Generator request UUID menghasilkan format yang tidak valid.')
  }
  return requestId
}

export class PendingMutationLock {
  private readonly pending = new Set<string>()

  isPending(requestId: string) {
    return this.pending.has(requestId)
  }

  async run<T>(requestId: string, operation: () => Promise<T>): Promise<T> {
    if (!isRequestId(requestId)) {
      throw new ClientAppError('INVALID_REQUEST_ID', 'request_uuid wajib berupa UUID yang valid.')
    }
    if (this.pending.has(requestId)) {
      throw new ClientAppError('MUTATION_IN_FLIGHT', 'Permintaan yang sama masih diproses.')
    }

    this.pending.add(requestId)
    try {
      return await operation()
    } finally {
      this.pending.delete(requestId)
    }
  }
}

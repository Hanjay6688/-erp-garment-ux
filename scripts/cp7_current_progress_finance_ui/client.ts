import {getUatSupabaseClient as originalClient} from './vendor/src/lib/supabase'
import {bindFrozenFinanceTransport} from './transport'

// Only the two vendored frozen panels resolve their client import here.
// AuthProvider/AuthGate retain the original authenticated Supabase client.
export function getUatSupabaseClient(...args: Parameters<typeof originalClient>) {
  return bindFrozenFinanceTransport(originalClient(...args))
}

/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_ERP_RUNTIME_MODE?: 'DEMO_SIMULATION' | 'UAT_AUTH_SIMULATION' | 'DISPOSABLE_TEST'
  readonly VITE_SUPABASE_URL?: string
  readonly VITE_SUPABASE_PUBLISHABLE_KEY?: string
  readonly VITE_SUPABASE_ANON_KEY?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

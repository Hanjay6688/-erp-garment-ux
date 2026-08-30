import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { AuthProvider } from './auth/AuthProvider'
import { AuthGate, RuntimeConfigurationFailure } from './auth/AuthGate'
import { parseRuntimeConfig } from './config/runtime'
import './styles.css'
import './auth/auth.css'
import './upgrade.css'
import './brand-books.css'
import './interaction-upgrades.css'
import './interaction-upgrades'
import './global-readability.css'
import './qc-final-sku.css'
import './procurement.css'
import './bs-rework'
import './workflow-refinements.css'
import './laundry.css'
import './workspace-refinements.css'
import './ux-corrections.css'
import './wip-control.css'

const root = ReactDOM.createRoot(document.getElementById('root')!)

try {
  // Never pass the complete Vite environment object to client code. Only these
  // four browser-safe values can participate in the bundle.
  const runtime = parseRuntimeConfig({
    VITE_ERP_RUNTIME_MODE: import.meta.env.VITE_ERP_RUNTIME_MODE,
    VITE_SUPABASE_URL: import.meta.env.VITE_SUPABASE_URL,
    VITE_SUPABASE_PUBLISHABLE_KEY: import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY,
    VITE_SUPABASE_ANON_KEY: import.meta.env.VITE_SUPABASE_ANON_KEY,
  })
  root.render(
    <React.StrictMode>
      <AuthProvider runtime={runtime}>
        <AuthGate><App /></AuthGate>
      </AuthProvider>
    </React.StrictMode>,
  )
} catch (error) {
  root.render(<RuntimeConfigurationFailure error={error} />)
}

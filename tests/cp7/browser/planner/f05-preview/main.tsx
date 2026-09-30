import { createRoot } from 'react-dom/client'
import F05App from './F05App'

// Deliberately isolated demo entry: no runtime config, auth, transport or ERP client.
createRoot(document.getElementById('root')!).render(<F05App runtimeMode="DEMO_SIMULATION" />)

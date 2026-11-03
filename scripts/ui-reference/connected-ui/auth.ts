/* Resolved only by the explicitly opted-in fixture Vite config. */
import {useSyncExternalStore} from 'react'
import {subscribe,getSnapshot} from './state'
export const useAuth=()=>useSyncExternalStore(subscribe,getSnapshot,getSnapshot)

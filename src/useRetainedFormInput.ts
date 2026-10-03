import { useCallback, useRef, useState, type Dispatch, type SetStateAction } from 'react'

// Session-only operator input. Never put workspace facts, read tickets,
// resolved catalogue rows, write envelopes or confirmation flags here.
export type RetainedFormInput = Record<string, unknown>
export function useRetainedFormInput(scope: string, committedSequence: number): RetainedFormInput {
  const current = useRef({ scope, committedSequence, fields: {} as RetainedFormInput })
  if (current.current.scope !== scope || current.current.committedSequence !== committedSequence) {
    current.current = { scope, committedSequence, fields: {} }
  }
  return current.current.fields
}

export function useRetainedInput<T>(fields: RetainedFormInput, key: string, initial: T): [T, Dispatch<SetStateAction<T>>] {
  const [value, setValue] = useState<T>(() => Object.hasOwn(fields, key) ? fields[key] as T : initial)
  const update = useCallback<Dispatch<SetStateAction<T>>>((action) => {
    setValue(current => {
      const next = typeof action === 'function' ? (action as (previous: T) => T)(current) : action
      // Old/unmounted callbacks retain only their old input object, so they
      // cannot populate a different actor or a newly committed form.
      fields[key] = next
      return next
    })
  }, [fields, key])
  return [value, update]
}

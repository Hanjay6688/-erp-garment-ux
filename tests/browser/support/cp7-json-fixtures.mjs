import { registerHooks } from 'node:module'

// Playwright runs these shared fixtures as Node ESM. Vite's JSON transform
// is absent there, so declare the type only for JSON under tests/fixtures.
const fixtures = new URL('../../fixtures/', import.meta.url).href
registerHooks({
  load(url, context, nextLoad) {
    if (url.startsWith(fixtures) && url.endsWith('.json')) {
      return nextLoad(url, { ...context, importAttributes: { ...context.importAttributes, type: 'json' } })
    }
    return nextLoad(url, context)
  },
})

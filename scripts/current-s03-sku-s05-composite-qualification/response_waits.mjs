// Observe rejection immediately while preserving the original promise/result.
// A timeout may close the browser while a click is still awaited. The response
// promise must not kill Node before the host's Auth cleanup can run.
export function observeResponseWaits(page) {
  const original = page.waitForResponse
  function observed(...args) {
    const pending = Reflect.apply(original, page, args)
    void pending.catch(() => {})
    return pending
  }
  page.waitForResponse = observed
  return () => { page.waitForResponse = original }
}

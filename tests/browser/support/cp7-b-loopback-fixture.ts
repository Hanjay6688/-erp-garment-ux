import { expect, test, type BrowserContext, type Page, type TestInfo } from '@playwright/test'

// Loopback fixture transport adapted from Writer B's 6e128ed2 operator browser run.
const appOrigin = 'http://127.0.0.1:4176'
const apiOrigin = 'http://127.0.0.1:54328'
const at = '2026-11-13T05:00:00Z'
export const fixtureActor = 'c6b00000-0000-4000-8000-000000000001'
const appUserId = 'c6b00000-0000-4000-8000-000000000002'

export type Call = { name: string; args: Record<string, any> }
export type Reply = { body: unknown; status?: number } | { abort: true }
export type Role = 'OWNER' | 'ADMIN' | 'STAFF'
type Transport = { calls: Call[]; unexpected: string[]; pageErrors: string[]; consoleErrors: string[] }
const transports = new WeakMap<BrowserContext, Transport>()

export async function mockApp(context: BrowserContext, config: {
  role: Role; rights: string[]; resolve: (call: Call) => Reply | undefined
}) {
  const actor = fixtureActor
  const calls: Call[] = [], unexpected: string[] = [], pageErrors: string[] = [], consoleErrors: string[] = []
  const transport = { calls, unexpected, pageErrors, consoleErrors }
  transports.set(context, transport)
  const encode = (value: unknown) => Buffer.from(JSON.stringify(value)).toString('base64url')
  const expires = Math.floor(Date.now() / 1000) + 3600
  const token = `${encode({ alg: 'HS256', typ: 'JWT' })}.${encode({ sub: actor, aud: 'authenticated', role: 'authenticated', exp: expires })}.cp7-fixture-signature`
  const user = {
    id: actor, aud: 'authenticated', role: 'authenticated', email: 'operator@example.test',
    email_confirmed_at: at, created_at: at, updated_at: at, app_metadata: { provider: 'email', providers: ['email'] },
    user_metadata: {}, identities: [],
  }
  const access = {
    allowed: true,
    profile: { id: appUserId, auth_user_id: actor, full_name: `Operator fixture ${config.role}`,
      role_id: 'c6b00000-0000-4000-8000-000000000003', role_code: config.role, role_name: config.role,
      is_active: true, row_version: 1, role_row_version: 1 },
    permissions: config.rights,
    external_portals: { mandor: 'NOT CONNECTED', laundry: 'NOT CONNECTED', store: 'NOT CONNECTED' },
  }
  const watch = (page: Page) => {
    page.on('pageerror', error => pageErrors.push(error.message))
    page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()) })
  }
  context.pages().forEach(watch)
  context.on('page', watch)
  await context.route('**/*', async route => {
    const request = route.request(), url = new URL(request.url())
    if (url.origin === appOrigin && ['GET', 'HEAD'].includes(request.method())) return route.continue()
    if (url.origin !== apiOrigin) {
      unexpected.push(`${request.method()} ${url.origin}${url.pathname}`)
      return route.abort('blockedbyclient')
    }
    const headers = { 'access-control-allow-origin': appOrigin,
      'access-control-allow-headers': request.headers()['access-control-request-headers'] ?? '*',
      'access-control-allow-methods': 'GET,POST,OPTIONS' }
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers })
    const send = (body: unknown, status = 200) => route.fulfill({ status, headers, json: body })
    if (url.pathname === '/auth/v1/token' && request.method() === 'POST') {
      return send({ access_token: token, token_type: 'bearer', expires_in: 3600, expires_at: expires,
        refresh_token: 'cp7-local-refresh-fixture', user })
    }
    if (url.pathname === '/auth/v1/user' && request.method() === 'GET') return send(user)
    if (url.pathname.startsWith('/rest/v1/rpc/') && request.method() === 'POST') {
      const name = url.pathname.split('/').at(-1)!
      const call = { name, args: request.postDataJSON() ?? {} }
      calls.push(call)
      if (name === 'erp_get_my_access_v1') return send(access)
      const reply = config.resolve(call)
      if (reply) return 'abort' in reply ? route.abort('failed') : send(reply.body, reply.status)
    }
    unexpected.push(`${request.method()} ${url.pathname}`)
    return send({ message: 'RPC fixture tidak dideklarasikan.' }, 404)
  })
  return transport
}

test.afterEach(async ({ context }, info) => {
  const transport = transports.get(context)
  if (transport && info.status !== 'passed') {
    await info.attach('transport-at-failure', { body: JSON.stringify(transport, null, 2), contentType: 'application/json' })
  }
})

export async function signIn(page: Page) {
  await page.goto('/')
  await page.getByLabel('Email akun ERP').fill('operator@example.test')
  await page.getByLabel('Kata sandi').fill('disposable-fixture-password')
  await page.getByRole('button', { name: 'Masuk', exact: true }).click()
  await expect(page.locator('.top-title strong')).toBeVisible()
}

export async function navigate(page: Page, group: string, label: string) {
  const parent = page.locator('.sidebar .nav-main').filter({ hasText: group }).first()
  await parent.waitFor({ state: 'attached' })
  const menu = page.getByRole('button', { name: 'Buka menu', exact: true })
  if (await menu.isVisible()) await menu.click()
  const link = page.getByRole('button', { name: `• ${label}`, exact: true })
  if (!await link.isVisible()) await parent.click()
  await link.click()
}

export async function capture(page: Page, info: TestInfo, name: string) {
  const viewport = page.viewportSize()!.width
  const width = await page.evaluate(() => ({ viewport: window.innerWidth, document: document.documentElement.scrollWidth }))
  await info.attach(`${name}-width`, { body: JSON.stringify(width), contentType: 'application/json' })
  await page.screenshot({ path: info.outputPath(`${name}.png`), fullPage: true, animations: 'disabled', scale: 'css' })
  expect.soft(width.viewport, `${name} viewport`).toBe(viewport)
  expect.soft(width.document, `${name} document`).toBeLessThanOrEqual(viewport)
}

export async function verifyTransport(mock: Awaited<ReturnType<typeof mockApp>>, info: TestInfo, expectedConsole: RegExp[] = []) {
  await info.attach('transport', { body: JSON.stringify(mock, null, 2), contentType: 'application/json' })
  expect(mock.unexpected).toEqual([])
  expect(mock.pageErrors).toEqual([])
  expect(mock.consoleErrors).toHaveLength(expectedConsole.length)
  expectedConsole.forEach((pattern, index) => expect(mock.consoleErrors[index]).toMatch(pattern))
}

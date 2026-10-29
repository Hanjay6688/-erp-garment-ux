// JSON-lines adapter for local in-memory PGlite only. No network or ERP fixture.
import { createRequire } from 'node:module'
import { createInterface } from 'node:readline'
const path = process.env.S05_PGLITE_MODULE
if (!path) throw new Error('S05_PGLITE_MODULE must select an already installed local module')
const { PGlite } = createRequire(import.meta.url)(path)
const db = new PGlite()
for await (const line of createInterface({ input: process.stdin, crlfDelay: Infinity })) {
  const request = JSON.parse(line)
  if (request.close) break
  try {
    let result
    if (request.params) {
      let index = 0
      result = await db.query(request.sql.replaceAll('%s', () => '$' + (++index)), request.params, { rowMode: 'array' })
    } else {
      const results = await db.exec(request.sql, { rowMode: 'array' })
      result = results.at(-1) || { rows: [], fields: [] }
    }
    const fields = (result.fields || []).map(field => field.name)
    process.stdout.write(JSON.stringify({ rows: result.rows }) + '\n')
  } catch (error) {
    process.stdout.write(JSON.stringify({ error: { code: error.code, message: error.message } }) + '\n')
  }
}
await db.close()

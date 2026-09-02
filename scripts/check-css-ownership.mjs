import assert from 'node:assert/strict'
import { readdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import postcss from 'postcss'

const root = process.cwd()
const sourceRoot = path.join(root, 'src')
const writeMode = process.argv.includes('--write')

async function walk(directory) {
  const entries = await readdir(directory, { withFileTypes: true })
  const files = await Promise.all(entries.map(async (entry) => {
    const target = path.join(directory, entry.name)
    return entry.isDirectory() ? walk(target) : [target]
  }))
  return files.flat()
}

function splitSelectors(selector) {
  const selectors = []
  let start = 0
  let depth = 0
  let quote = ''
  for (let index = 0; index < selector.length; index += 1) {
    const character = selector[index]
    if (quote) {
      if (character === quote && selector[index - 1] !== '\\') quote = ''
      continue
    }
    if (character === '"' || character === "'") quote = character
    else if (character === '(' || character === '[') depth += 1
    else if (character === ')' || character === ']') depth -= 1
    else if (character === ',' && depth === 0) {
      selectors.push(selector.slice(start, index).trim())
      start = index + 1
    }
  }
  selectors.push(selector.slice(start).trim())
  return selectors.filter(Boolean)
}

const files = await walk(sourceRoot)
const componentFiles = files.filter((file) => /\.(?:ts|tsx)$/.test(file) && !/\.(?:test|spec)\.(?:ts|tsx)$/.test(file))
const cssFiles = files.filter((file) => file.endsWith('.css'))
const componentSource = (await Promise.all(componentFiles.map((file) => readFile(file, 'utf8')))).join('\n')
const classPattern = /\.([A-Za-z_][\w-]*)/g
const findings = []
let removedSelectors = 0
let removedRules = 0

for (const file of cssFiles) {
  const original = await readFile(file, 'utf8')
  const sheet = postcss.parse(original, { from: file })
  sheet.walkRules((rule) => {
    const selectors = splitSelectors(rule.selector)
    const owned = []
    for (const selector of selectors) {
      const classes = [...new Set([...selector.matchAll(classPattern)].map((match) => match[1]))]
      const unowned = classes.length > 0 && classes.every((className) => !componentSource.includes(className))
      if (unowned) {
        findings.push(`${path.relative(root, file)}: ${selector}`)
        removedSelectors += 1
      } else {
        owned.push(selector)
      }
    }
    if (!writeMode) return
    if (owned.length === 0) {
      rule.remove()
      removedRules += 1
    } else if (owned.length !== selectors.length) {
      rule.selector = owned.join(', ')
    }
  })
  if (writeMode) {
    sheet.walkAtRules((rule) => {
      if (rule.nodes?.length === 0) rule.remove()
    })
    await writeFile(file, sheet.toString())
  }
}

if (writeMode) {
  console.log(`CSS ownership prune completed: ${removedSelectors} selectors and ${removedRules} empty rules removed.`)
} else {
  assert.deepEqual(findings, [], `Unowned CSS selectors:\n${findings.join('\n')}`)
  console.log(`CSS ownership passed: ${cssFiles.length} stylesheets have no unowned selector branches.`)
}

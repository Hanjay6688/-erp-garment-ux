// Generates the mirrored block of src/ux-rapih.css (type scale, box borders, text contrast).
//
// Why a mirror: the ERP stylesheets contain ~1.500 font-size declarations below
// 12px (6–11px labels), ~20 different sizes, 15 font weights and a serif family
// spread over 30+ files, often with !important. To apply ONE type standard
// (docs/UX_STANDARD.md) WITHOUT editing those files — the old look must stay
// one class away — every font-size / font / line-height / font-weight /
// font-family declaration is mirrored under `.ux-rapih` with the same
// importance and context (@media/@supports), in the same relative order.
// Every mirror has exactly one extra class of specificity, so the winner among
// mirrors is always the mirror of the original winner; only the values change:
//   font-size   px < 28 → nearest step of the scale (--fs-xs 12 … --fs-xl 24),
//               never below 12px; ≥ 28px display sizes and clamp()/em stay.
//   line-height unitless → 1.4–1.5 for text ≤ 16px, ≥ 1.15 for larger text.
//   font-weight → 400 / 600 / 700.   font-family → --font-sans / --font-mono.
//   border*     faint separators get visible: low-alpha rgba +0.08 alpha,
//               dark neutral hex borders mixed 22% toward #aab6e0.
//   color       mid-tone text (contrast 1.8–4.7 on the lighter card #212a42) is
//               lightened, hue kept, until it reaches 4.7:1. Near-black text
//               (meant for light chips/avatars) is left alone.
//
//   node scripts/generate-ux-rapih.mjs          rewrite the block
//   node scripts/generate-ux-rapih.mjs --check  fail when the block is stale
import assert from 'node:assert/strict'
import { readFile, readdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import postcss from 'postcss'

const root = process.cwd()
const sourceRoot = path.join(root, 'src')
const targetFile = path.join(sourceRoot, 'ux-rapih.css')
const checkMode = process.argv.includes('--check')
const START = '/* @generated ux-rapih-mirror:start — do not edit by hand; run `npm run gen:ux-rapih` */'
const END = '/* @generated ux-rapih-mirror:end */'
const ROOT_CLASS = '.ux-rapih'
const SCALE = [[12, 'xs'], [13, 'sm'], [14, 'base'], [16, 'md'], [20, 'lg'], [24, 'xl']]
const DISPLAY_FROM_PX = 28
const MIRRORED = new Set(['font-size', 'font', 'line-height', 'font-weight', 'font-family', 'color'])
const BORDER_PROP = /^border(-(top|right|bottom|left))?(-color)?$/
const TEXT_REFERENCE_BG = [0x21, 0x2a, 0x42]
const TEXT_TARGET_RATIO = 4.7
const TEXT_LIGHT_SURFACE_RATIO = 1.8

async function walk(directory) {
  const entries = await readdir(directory, { withFileTypes: true })
  const nested = await Promise.all(entries.map((entry) => {
    const target = path.join(directory, entry.name)
    return entry.isDirectory() ? walk(target) : [target]
  }))
  return nested.flat()
}

// Bundle order: CSS in module-evaluation order, the way Vite emits it. Static
// imports are walked depth-first in source order starting at main.tsx (a JS
// import's stylesheets come before the importer's later CSS imports); lazy
// `import('./X')` chunks follow, in the order they are referenced. Keeping
// this order means mirrored rules tie-break exactly like the originals.
async function orderedStylesheets() {
  const all = (await walk(sourceRoot)).filter((file) => file.endsWith('.css') && file !== targetFile)
  const ordered = []
  const visited = new Set()
  const lazyQueue = []
  const resolveModule = async (from, specifier) => {
    const base = path.resolve(path.dirname(from), specifier)
    for (const candidate of [base, `${base}.tsx`, `${base}.ts`, path.join(base, 'index.tsx'), path.join(base, 'index.ts')]) {
      try { await readFile(candidate); return candidate } catch { /* try next */ }
    }
    return null
  }
  const visit = async (file) => {
    if (visited.has(file)) return
    visited.add(file)
    const source = await readFile(file, 'utf8')
    const pattern = /import\s+(type\s+)?(?:[^'";]*?\s+from\s+)?['"](\.[^'"]+)['"]|import\(\s*['"](\.[^'"]+)['"]\s*\)/g
    for (const raw of source.matchAll(pattern)) {
      if (raw[1]) continue // `import type` is erased by the compiler
      const match = [raw[0], raw[2], raw[3]]
      if (match[2]) { lazyQueue.push([file, match[2]]); continue }
      const specifier = match[1]
      if (specifier.endsWith('.css')) {
        const css = path.resolve(path.dirname(file), specifier)
        if (!ordered.includes(css) && css !== targetFile) ordered.push(css)
        continue
      }
      const target = await resolveModule(file, specifier)
      if (target && !/\.test\.tsx?$/.test(target)) await visit(target)
    }
  }
  await visit(path.join(sourceRoot, 'main.tsx'))
  while (lazyQueue.length) {
    const [from, specifier] = lazyQueue.shift()
    const target = await resolveModule(from, specifier)
    if (target) await visit(target)
  }
  return [...ordered.filter((file) => all.includes(file)), ...all.filter((file) => !ordered.includes(file)).sort()]
}

function splitSelectors(selector) {
  const selectors = []
  let start = 0
  let depth = 0
  for (let index = 0; index < selector.length; index += 1) {
    const character = selector[index]
    if (character === '(' || character === '[') depth += 1
    else if (character === ')' || character === ']') depth -= 1
    else if (character === ',' && depth === 0) {
      selectors.push(selector.slice(start, index).trim())
      start = index + 1
    }
  }
  selectors.push(selector.slice(start).trim())
  return selectors.filter(Boolean)
}

function scopeSelector(selector) {
  if (/^:root\b/.test(selector)) return selector.replace(/^:root/, `:root${ROOT_CLASS}`)
  if (/^html\b/.test(selector)) return selector.replace(/^html/, `html${ROOT_CLASS}`)
  return `${ROOT_CLASS} ${selector}`
}

// Nearest step of the type scale (ties go up); null = keep the original value.
function scaleStep(px) {
  if (px >= DISPLAY_FROM_PX) return null
  if (px <= SCALE[0][0]) return SCALE[0]
  return SCALE.reduce((best, step) => Math.abs(step[0] - px) <= Math.abs(best[0] - px) ? step : best)
}
function snapFontSize(value) {
  const match = /^\s*(\d*\.?\d+)px\s*$/.exec(value)
  if (!match) return value
  const step = scaleStep(Number(match[1]))
  return step ? `var(--fs-${step[1]})` : value
}
function snapLineHeight(value, sizePx) {
  const trimmed = value.trim()
  if (!/^\d*\.?\d+$/.test(trimmed)) return value
  const lineHeight = Number(trimmed)
  if (sizePx !== null && sizePx >= 20) return String(Math.max(1.15, lineHeight))
  return String(Math.min(1.5, Math.max(1.4, lineHeight)))
}
function snapWeight(value) {
  const trimmed = value.trim().toLowerCase()
  if (trimmed === 'normal') return '400'
  if (trimmed === 'bold') return '700'
  if (!/^\d+$/.test(trimmed)) return value
  const weight = Number(trimmed)
  return weight < 500 ? '400' : weight < 650 ? '600' : '700'
}
function snapFamily(value) {
  if (/^(inherit|initial|unset|revert)$/i.test(value.trim())) return value
  return /mono|courier|consolas|menlo/i.test(value) ? 'var(--font-mono)' : 'var(--font-sans)'
}
function snapFontShorthand(value) {
  if (/^(inherit|initial|unset|revert)$/i.test(value.trim())) return value
  return value
    .replace(/(\d*\.?\d+)px(\s*\/\s*(\d*\.?\d+)(?![\w%.]))?/, (match, size, slashPart, lineHeight) => {
      const step = scaleStep(Number(size))
      const nextSize = step ? `${step[0]}px` : `${size}px`
      return slashPart ? `${nextSize}/${snapLineHeight(lineHeight, step ? step[0] : Number(size))}` : nextSize
    })
    .replace(/\b([1-9]00)\b(?=\s)/, (weight) => snapWeight(weight))
    .replace(/(,|\s)(Georgia|serif)\b.*$/i, '$1var(--font-sans)')
}
// Border colours: make faint separators visible without changing hue.
function boostBorderColor(color) {
  const rgba = /^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)$/i.exec(color)
  if (rgba) {
    const [r, g, b] = rgba.slice(1, 4).map(Number)
    const alpha = rgba[4] === undefined ? 1 : Number(rgba[4])
    if (alpha >= 0.3) return color
    const white = r > 240 && g > 240 && b > 240
    const next = Math.min(white ? 0.22 : 0.4, alpha + 0.08)
    return `rgba(${r},${g},${b},${Number(next.toFixed(3))})`
  }
  const hex = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(color)
  if (!hex) return color
  const full = hex[1].length === 3 ? hex[1].split('').map((c) => c + c).join('') : hex[1]
  const [r, g, b] = [0, 2, 4].map((index) => parseInt(full.slice(index, index + 2), 16))
  const max = Math.max(r, g, b); const min = Math.min(r, g, b)
  // only dark, low-saturation neutrals (the dark theme's separators)
  if (max > 0x5a || max - min > 0x28) return color
  const target = [0xaa, 0xb6, 0xe0]
  const mixed = [r, g, b].map((channel, index) => Math.round(channel + (target[index] - channel) * 0.22))
  return `#${mixed.map((channel) => channel.toString(16).padStart(2, '0')).join('')}`
}
function boostBorder(value) {
  return value.replace(/rgba?\([^)]*\)|#[0-9a-f]{3,6}\b/gi, (color) => boostBorderColor(color))
}

// Text colours: lift mid-tones to ≥ 4.6:1 on the dark card surface.
const channel = (value) => { const v = value / 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4 }
const luminance = ([r, g, b]) => 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
const contrast = (a, b) => { const [l1, l2] = [luminance(a), luminance(b)].sort((x, y) => y - x); return (l1 + 0.05) / (l2 + 0.05) }
const mix = (from, to, amount) => from.map((value, index) => Math.round(value + (to[index] - value) * amount))
function liftTextColor(color) {
  const rgba = /^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)$/i.exec(color)
  const hex = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(color)
  let rgb; let alpha = 1
  if (rgba) { rgb = rgba.slice(1, 4).map(Number); alpha = rgba[4] === undefined ? 1 : Number(rgba[4]) }
  else if (hex) { const full = hex[1].length === 3 ? hex[1].split('').map((c) => c + c).join('') : hex[1]; rgb = [0, 2, 4].map((index) => parseInt(full.slice(index, index + 2), 16)) }
  else return color
  const effective = alpha < 1 ? mix(TEXT_REFERENCE_BG, rgb, alpha) : rgb
  const ratio = contrast(effective, TEXT_REFERENCE_BG)
  if (ratio >= TEXT_TARGET_RATIO || ratio < TEXT_LIGHT_SURFACE_RATIO) return color
  // mix toward a light tint of the same hue until the target ratio is met
  const tint = mix(effective, [244, 246, 252], 0.85)
  for (let step = 1; step <= 40; step += 1) {
    const candidate = mix(effective, tint, step / 40)
    if (contrast(candidate, TEXT_REFERENCE_BG) >= TEXT_TARGET_RATIO) return `#${candidate.map((value) => value.toString(16).padStart(2, '0')).join('')}`
  }
  return '#c9d0df'
}
function liftText(value) {
  return value.replace(/rgba?\([^)]*\)|#[0-9a-f]{3,6}\b/gi, (color) => liftTextColor(color))
}

function ruleFontSizePx(declarations) {
  const sizeDeclaration = declarations.find((declaration) => declaration.prop.toLowerCase() === 'font-size')
  const match = sizeDeclaration && /^\s*(\d*\.?\d+)px/.exec(sizeDeclaration.value)
  if (!match) return null
  const step = scaleStep(Number(match[1]))
  return step ? step[0] : Number(match[1])
}
function mirroredValue(prop, value, sizePx) {
  if (BORDER_PROP.test(prop)) return boostBorder(value)
  if (prop === 'color') return liftText(value)
  if (prop === 'font-size') return snapFontSize(value)
  if (prop === 'line-height') return snapLineHeight(value, sizePx)
  if (prop === 'font-weight') return snapWeight(value)
  if (prop === 'font-family') return snapFamily(value)
  return snapFontShorthand(value)
}

function contextOf(node) {
  const chain = []
  for (let parent = node.parent; parent && parent.type !== 'root'; parent = parent.parent) {
    if (parent.type === 'atrule') {
      if (/keyframes$/i.test(parent.name)) return null
      chain.unshift(`@${parent.name} ${parent.params}`)
    }
  }
  return chain
}

const output = []
let mirroredDeclarations = 0
let normalisedDeclarations = 0
for (const file of await orderedStylesheets()) {
  const sheet = postcss.parse(await readFile(file, 'utf8'), { from: file })
  const blocks = []
  sheet.walkRules((rule) => {
    const context = contextOf(rule)
    if (!context) return
    const declarations = rule.nodes.filter((node) => node.type === 'decl' && (MIRRORED.has(node.prop.toLowerCase()) || BORDER_PROP.test(node.prop.toLowerCase())))
    if (declarations.length === 0) return
    const sizePx = ruleFontSizePx(declarations)
    const body = declarations.map((declaration) => {
      const value = mirroredValue(declaration.prop.toLowerCase(), declaration.value, sizePx)
      mirroredDeclarations += 1
      if (value !== declaration.value) normalisedDeclarations += 1
      return `${declaration.prop}:${value}${declaration.important ? '!important' : ''}`
    }).join(';')
    const selector = splitSelectors(rule.selector).map(scopeSelector).join(',')
    const css = `${selector}{${body}}`
    blocks.push(context.reduceRight((inner, atRule) => `${atRule}{${inner}}`, css))
  })
  if (blocks.length) output.push(`/* ${path.relative(sourceRoot, file)} */`, ...blocks)
}

const generated = [START, `/* ${mirroredDeclarations} declarations mirrored, ${normalisedDeclarations} normalised (type scale / visible borders / text contrast). */`, ...output, END].join('\n')
const current = await readFile(targetFile, 'utf8')
const startIndex = current.indexOf(START)
const endIndex = current.indexOf(END)
assert.ok(startIndex >= 0 && endIndex > startIndex, `${path.relative(root, targetFile)} is missing the generated block markers`)
const next = `${current.slice(0, startIndex)}${generated}${current.slice(endIndex + END.length)}`

if (checkMode) {
  assert.equal(current, next, 'src/ux-rapih.css mirrored block is stale. Run `npm run gen:ux-rapih` after changing font or border declarations in any stylesheet.')
  console.log(`ux-rapih mirror is current: ${mirroredDeclarations} declarations mirrored, ${normalisedDeclarations} normalised.`)
} else {
  await writeFile(targetFile, next)
  console.log(`ux-rapih mirror regenerated: ${mirroredDeclarations} declarations mirrored, ${normalisedDeclarations} normalised.`)
}

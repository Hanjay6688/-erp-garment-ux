import assert from 'node:assert/strict'

// Afui measures the text drawn by the settings panel. Native checkbox and
// radio values are form metadata. Their visible label text is still measured.
export async function readable(panel) {
  const observed = await panel.evaluate(root => {
    const rgb = value => value.match(/[\d.]+/g).map(Number)
    const luminance = color => color.slice(0, 3).map(channel => channel / 255)
      .map(channel => channel <= .04045 ? channel / 12.92 : ((channel + .055) / 1.055) ** 2.4)
      .reduce((sum, channel, index) => sum + channel * [.2126, .7152, .0722][index], 0)
    const rows = [], exempt = []
    for (const element of [root, ...root.querySelectorAll('*')]) {
      const style = getComputedStyle(element)
      const text = [...element.childNodes].filter(node => node.nodeType === Node.TEXT_NODE)
        .map(node => node.textContent).join(' ').trim()
      const hasTextValue = element instanceof HTMLTextAreaElement ||
        (element instanceof HTMLInputElement && ['date', 'text'].includes(element.type))
      const label = text || (hasTextValue ? element.value : '')
      if (!label || !element.getClientRects().length || style.visibility !== 'visible' || element.tagName === 'OPTION') continue
      const sample = label.slice(0, 100)
      if (element.closest(':disabled,[aria-disabled="true"]')) {
        exempt.push({label: sample, reason: 'INACTIVE_CONTROL_WCAG_CONTRAST_EXEMPTION'})
        continue
      }
      const layers = []
      let background = null
      for (let ancestor = element; ancestor; ancestor = ancestor.parentElement) {
        const surface = getComputedStyle(ancestor), color = rgb(surface.backgroundColor)
        if (surface.backgroundImage !== 'none' || surface.opacity !== '1') {
          throw Error('UNMEASURED_AFUI_TEXT_SURFACE:' + JSON.stringify({label: sample,
            tag: ancestor.tagName, classes: ancestor.className, backgroundImage: surface.backgroundImage, opacity: surface.opacity}))
        }
        if (color.length === 3 || color[3] === 1) {
          background = color.slice(0, 3)
          break
        }
        layers.push(color)
      }
      if (!background) throw Error('MISSING_AFUI_TEXT_SURFACE')
      for (const color of layers.reverse()) {
        background = background.map((channel, index) => color[index] * color[3] + channel * (1 - color[3]))
      }
      const foreground = rgb(style.color), alpha = foreground[3] ?? 1
      const visible = background.map((channel, index) => foreground[index] * alpha + channel * (1 - alpha))
      const a = luminance(visible), b = luminance(background)
      rows.push({label: sample, ratio: (Math.max(a, b) + .05) / (Math.min(a, b) + .05),
        foreground: style.color, background})
    }
    return {rows, exempt}
  })
  assert.ok(observed.rows.length > 0, 'NO_VISIBLE_AFUI_TEXT_MEASURED')
  assert.deepEqual(observed.rows.filter(row => row.ratio < 4.5), [], 'AFUI_TEXT_CONTRAST_BELOW_4_5')
  return observed
}

export async function reviewContrastPreflight(page) {
  await page.setContent(`<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <section style="background:rgb(13,24,40);color:white">
      <label><input type="checkbox" style="color:black">Konfirmasi tanggal berlaku</label>
      <input aria-label="Tanggal berlaku" type="date" value="2026-11-07">
      <textarea aria-label="Alasan">Alasan tercatat</textarea>
      <button>Browser prerequisite</button>
    </section>`)
  const panel = page.locator('section'), label = panel.locator('label')
  assert.equal(await label.locator('input').inputValue(), 'on')
  const {rows} = await readable(panel)
  for (const text of ['Konfirmasi tanggal berlaku', '2026-11-07', 'Alasan tercatat']) {
    assert.ok(rows.some(row => row.label === text), 'AFUI_RENDERED_TEXT_MUST_BE_MEASURED:' + text)
  }
  assert.ok(rows.every(row => row.label !== 'on'), 'AFUI_CHECKBOX_FORM_VALUE_IS_NOT_TEXT')
  await label.evaluate(element => { element.style.color = 'black' })
  await assert.rejects(readable(panel), /AFUI_TEXT_CONTRAST_BELOW_4_5/)
  return {checkbox_label_measured: true, visible_low_contrast_refused: true, contrast_minimum: 4.5}
}

  const browser = await chromium.launch({executablePath:process.env.CHROME_BIN})
  try {
    const ctxA = await browser.newContext({timezoneId:'America/Los_Angeles'})
    const ctxB = await browser.newContext({timezoneId:'Asia/Jakarta'})
    const a = await ctxA.newPage(), b = await ctxB.newPage()
    const button = (p,name) => p.getByRole('button',{name,exact:true})
    const visible = p => p.getByRole('region',{name:'Daftar pengingat'})
    const labels = p => visible(p).locator('article').evaluateAll(nodes=>nodes.map(n=>n.getAttribute('aria-label').slice('Pengingat '.length)))
    async function ready(p) {
      await expect(visible(p)).toBeVisible()
      await expect(p.getByText('Memuat pengingat…',{exact:true})).toHaveCount(0)
    }
    async function open(p) {await p.goto(origin);await button(p,'Belum selesai').click();await ready(p)}
    async function next(p) {await button(p,'Pengingat berikutnya').click();await ready(p)}
    async function change(p,title,at) {
      await button(p,'Ubah '+title).click()
      await p.getByLabel('Jatuh tempo pengingat (WIB)',{exact:true}).fill(at)
      await button(p,'Simpan perubahan').click()
      await expect(p.getByText(/Perubahan pengingat .* disimpan\./)).toBeVisible()
      await ready(p)
    }
    await ctl('/seed',{n:51})
    await open(a)
    const before = await ctl('/facts'), idByTitle = new Map(before.map(r=>[r.title,r.id]))
    assert.equal(idByTitle.size,51)
    const ids = async p => {
      const rows=(await labels(p)).map(t=>idByTitle.get(t));assert.ok(rows.every(Boolean));return rows
    }
    const first = await ids(a); await next(a); const middle = await ids(a)
    assert.deepEqual([...first,...middle],before.slice(0,50).map(r=>r.id))
    await open(b);await change(b,'R0','2041-01-01T12:05');await next(b);await change(b,'R50','2020-01-01T09:00')
    const after=await ctl('/facts'), ordered=after.map(r=>r.id)
    assert.deepEqual(ordered,[before[50].id,...before.slice(1,50).map(r=>r.id),before[0].id])
    assert.deepEqual(middle,ordered.slice(25,50))
    await next(a)
    await expect(a.getByText('Urutan pengingat berubah. Daftar terbaru ditampilkan dari awal.',{exact:true})).toBeVisible()
    await expect(a.getByText('1–25 dari 51',{exact:true})).toBeVisible()
    const pages=[await ids(a)];await next(a);pages.push(await ids(a));await next(a);pages.push(await ids(a))
    assert.deepEqual(pages.flat(),ordered);assert.equal(new Set(pages.flat()).size,51)
    const committed=(await ctl('/facts')).map(r=>r.id);assert.deepEqual(committed,ordered)
    record({id:'automatic-restart-51-ids',outcome:'PASS',before:before.map(r=>r.id),after:ordered,middleBefore:middle,
      middleAfter:ordered.slice(25,50),firstAfter:after[0].title,lastAfter:after.at(-1).title,notified:true,
      recovery:'automatic',displayedIdsByPage:pages,rereadFromAnotherConnection:committed,seenExactlyOnce:51})
  } finally {await browser.close()}
}
run().catch(error=>{console.error(error);process.exitCode=1})

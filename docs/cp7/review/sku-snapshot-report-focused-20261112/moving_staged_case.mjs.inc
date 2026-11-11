  await run('B_TWO_LATE_COSTS_TWO_STAGED_RETURNS', 2, async (result, original) => {
    const state = (pcs, hpp, fg, cogs) => ({ pcs, hpp, fg, cogs, other: 0 });
    const returnJournal = amount => ({
      FG_INVENTORY: amount, COGS: -amount, SALES_REVENUE: salePriceCents, AR_CUSTOMER: -salePriceCents,
    });
    const value = async returned => Number((await returnSnapshot(returned))[0].effective_value);

    let before = await journalIds();
    await costReconcile('3.01');
    await observe(result, 'late_cost_1', state(0, 7301, 0, 7301), before,
      { COGS: 101, MATERIAL_COST_OFFSET: -101 });
    before = await journalIds();
    const first = await returnOne(1, x.saleA, x.root50);
    await observe(result, 'return_1', state(1, 7301, 3651, 3650), before, returnJournal(3651));
    assert.equal(await value(first), 36.51);
    const firstFrozen = await returnSnapshot(first);

    before = await journalIds();
    await costReconcile('4.03');
    await observe(result, 'late_cost_2', state(1, 7403, 3702, 3701), before,
      { FG_INVENTORY: 51, COGS: 51, MATERIAL_COST_OFFSET: -102 });
    assert.deepEqual(await returnSnapshot(first), firstFrozen);
    await sameAmountReplay(result, '4.03');

    before = await journalIds();
    const second = await returnOne(2, x.saleB, x.converted);
    await observe(result, 'return_2', state(2, 7403, 7403, 0), before, returnJournal(3701));
    assert.equal(await value(second), 37.01);
    const secondFrozen = await returnSnapshot(second);

    before = await journalIds();
    await costReconcile('3.01');
    await observe(result, 'reverse_second_source_delta', state(2, 7301, 7301, 0), before,
      { FG_INVENTORY: -102, MATERIAL_COST_OFFSET: 102 });
    assert.deepEqual(await returnSnapshot(first), firstFrozen);
    assert.deepEqual(await returnSnapshot(second), secondFrozen);
    assert.deepEqual(await allocationSnapshot(), original);
    result.sale_and_return_snapshots_immutable = true;
    result.original_return_values = ['36.51', '37.01'];
    result.second_source_delta_inverse_model = true;
  });

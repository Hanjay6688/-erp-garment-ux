def fetch(cur, run_id, subject=None):
    """Page set plus every page, verified exactly as the client does; returns the reassembled Original."""
    ps = limited(cur, 'erp_cp7_read_staged_analysis_pages_v1', (run_id,), subject)
    assert ps['contract_version'] == 'cp7.native-analysis-pages.v1' and ps['run_id'] == str(run_id), ps.get('contract_version')
    assert ps['apply_enabled'] is False and ps['production_go'] is False and len(ps['access_epoch']) == 64
    assert 'document' not in ps and 'semantic_hash' not in ps, 'P19G_STAGED_RUN_CLAIMS_A_WHOLE_DOCUMENT'
    h = ps['header']
    assert len(h['body'].encode('utf8')) == h['utf8_bytes'] <= PAGE_BYTES and sha(h['body']) == h['sha256']
    header = parse(h['body'])
    assert header['contract_version'] == 'cp7.native-analysis-header.v1' and header['run_id'] == str(run_id)
    assert header['request_id'] == ps['request_id'] and header['financial_source'] is None
    assert (header['targets_total'], header['page_count'], header['paged']) == (ps['targets_total'], ps['page_count'], ps['paged'])
    assert header['apply_enabled'] is False and header['production_go'] is False
    pages = ps['pages']
    assert [p['index'] for p in pages] == list(range(ps['page_count'])) and ps['page_count'] >= 1
    assert ps['identity_hash'] == sha(h['sha256'] + '\n' + '\n'.join(p['sha256'] for p in pages)), 'P19G_IDENTITY_HASH'
    nxt, bodies, sizes = 1, [], []
    for entry in pages:
        assert entry['target_lo'] == nxt and entry['target_hi'] >= entry['target_lo'], entry
        nxt = entry['target_hi'] + 1
        e = limited(cur, 'erp_cp7_read_staged_analysis_page_v1', (run_id, entry['index'], ps['access_epoch']), subject)
        assert (e['contract_version'], e['run_id'], e['index'], e['page_count'], e['target_lo'], e['target_hi'], e['header_sha256'],
                e['identity_hash']) == ('cp7.native-analysis-page-read.v1', str(run_id), entry['index'], ps['page_count'],
                                        entry['target_lo'], entry['target_hi'], h['sha256'], ps['identity_hash']), e.get('index')
        raw = e['body'].encode('utf8')
        assert len(raw) == e['utf8_bytes'] == entry['utf8_bytes'] <= PAGE_BYTES and sha(e['body']) == e['sha256'] == entry['sha256']
        page = parse(e['body'])
        assert page['contract_version'] == 'cp7.native-analysis-page.v1' and page['run_id'] == str(run_id)
        assert (page['index'], page['target_lo'], page['target_hi'], page['targets_total'], page['header_sha256']) == (
            entry['index'], entry['target_lo'], entry['target_hi'], ps['targets_total'], h['sha256'])
        assert page['counts'] == entry['counts'] and page['apply_enabled'] is False and page['production_go'] is False
        bodies.append(page)
        sizes.append(len(raw))
    assert nxt - 1 == ps['targets_total'], ('P19G_PAGES_DO_NOT_COVER_EVERY_TARGET', nxt - 1, ps['targets_total'])
    # Reassemble: each paged array is its header prefix followed by every
    # page's items in page order; everything else is the header's.
    whole = dict(header['analysis_header'])
    for name, layout in header['paged'].items():
        prefix = whole[name]
        assert len(prefix) == layout['prefix'], (name, len(prefix), layout)
        items = [x for page in bodies for x in page['items'].get(name, [])]
        assert len(items) == layout['items'], (name, len(items), layout)
        whole[name] = prefix + items
    original = dict(contract_version='cp7.native-analysis-run.v1', run_id=header['run_id'], request_id=header['request_id'],
                    analysis=whole, product_labels=header['product_labels'], query=header['query'],
                    financial_source=header['financial_source'], apply_enabled=False, production_go=False)
    return original, ps, dict(page_count=ps['page_count'], targets_total=ps['targets_total'], header_utf8_bytes=h['utf8_bytes'],
                              page_utf8_bytes_max=max(sizes), page_utf8_bytes_total=sum(sizes),
                              uneven_ranges=len({p['target_hi'] - p['target_lo'] for p in pages}) > 1)

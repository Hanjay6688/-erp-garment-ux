import type { AnalysisResult } from '../contract'

type TimelineDay = AnalysisResult['timeline'][number]
type Arrivals = Partial<Record<'directed_supply' | 'candidate_supply' | 'proposed_new_supply', string>>

function assumedPieces(value: string) {
  return {
    state: 'ASSUMED' as const,
    value,
    unit: 'PCS',
    refs: [{ kind: 'ANALYSIS', id: 'fixture-timeline', revision: 'v2' }],
    assumption_ids: ['FIXTURE_POLICY_AND_ETA'],
  }
}

function day(date: string, closing: string, minimum: string, arrivals: Arrivals = {}): TimelineDay {
  return {
    date,
    target_key: 'fixture-vivo:A:30',
    demand: assumedPieces('4'),
    directed_supply: assumedPieces(arrivals.directed_supply ?? '0'),
    candidate_supply: assumedPieces(arrivals.candidate_supply ?? '0'),
    proposed_new_supply: assumedPieces(arrivals.proposed_new_supply ?? '0'),
    balance_end: assumedPieces(closing),
    mode: 'BACKLOG',
    assumed: true,
    unmet_demand: assumedPieces('0'),
    backlog_qty: assumedPieces('0'),
    min_intraday_balance: assumedPieces(minimum),
    first_gap_at: null,
    timing_basis: 'DATE_POLICY',
    timing_policy_id: 'FIXTURE_ARRIVALS_BEFORE_DAILY_DEMAND',
    event_refs: [],
  }
}

export const exampleTimeline = [
  day('2026-10-01', '14', '14'),
  day('2026-10-02', '10', '10'),
  day('2026-10-03', '18', '10', { directed_supply: '12' }),
  day('2026-10-04', '14', '14'),
  day('2026-10-05', '10', '10'),
  day('2026-10-06', '16', '10', { candidate_supply: '10' }),
  day('2026-10-07', '20', '16', { proposed_new_supply: '8' }),
  day('2026-10-08', '16', '16'),
  day('2026-10-09', '12', '12'),
  day('2026-10-10', '8', '8'),
]

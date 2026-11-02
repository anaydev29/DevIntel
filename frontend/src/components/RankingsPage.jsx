import { useEffect, useMemo, useState } from 'react'
import { categoryName, growthText } from '../lib/format'
import { loadBreakdown } from '../lib/api'
import {
  DEFAULT_WEIGHTS,
  loadStoredWeights,
  onWeightsChange,
  scoreFor,
  sharesDiffer,
  storeWeights,
} from '../lib/score'
import Page from './Page'
import WeightCustomizer from './WeightCustomizer'

const PAGE_SIZE = 10

const SORTS = {
  score: ['Score, high to low', (a, b) => (b.devintel_score ?? 0) - (a.devintel_score ?? 0)],
  growth: ['Growth, high to low', (a, b) => (a.growth_30d == null) - (b.growth_30d == null) || (b.growth_30d ?? 0) - (a.growth_30d ?? 0)],
  name: ['Name, A to Z', (a, b) => a.name.localeCompare(b.name)],
}

// Page numbers with gaps, for example 1 2 3 ... 11
function pageList(total, current) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const nums = [...new Set([1, total, current - 1, current, current + 1])]
    .filter((n) => n >= 1 && n <= total)
    .sort((a, b) => a - b)
  const out = []
  nums.forEach((n, i) => {
    if (i && n - nums[i - 1] > 1) out.push('gap')
    out.push(n)
  })
  return out
}

function Row({ rank, tech, onSelect }) {
  const growth = growthText(tech.growth_30d)
  return (
    <li>
      <button type="button" className="di-row di-row--full" onClick={() => onSelect(tech.slug)}>
        <span className={`di-rank di-rank--${rank <= 3 ? rank : 'x'}`}>{rank}</span>
        <span className="di-row__name">
          {tech.name}
          <span className="di-chip bg-lilac">{categoryName(tech.category)}</span>
          {tech.is_emerging && <span className="di-chip bg-hot">Taking off</span>}
        </span>
        <span className="di-bar">
          <span className="di-bar__track"><span className="di-bar__fill" style={{ display: 'block', width: `${Math.max(2, tech.devintel_score ?? 0)}%` }} /></span>
          <span className="di-bar__num">{Math.round(tech.devintel_score ?? 0)}</span>
        </span>
        <span
          className={`di-growth ${growth == null ? 'di-growth--na' : tech.growth_30d > 0 ? 'di-growth--up' : ''}`}
          title={growth == null ? 'Growth needs at least 7 days of collected history' : undefined}
        >
          {growth ?? 'n/a'}
        </span>
      </button>
    </li>
  )
}

export default function RankingsPage({ data, onSelect }) {
  const [category, setCategory] = useState('all')
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState('score')
  const [page, setPage] = useState(1)
  const [panelOpen, setPanelOpen] = useState(false)
  const [breakdown, setBreakdown] = useState(null)
  const [weights, setWeights] = useState(() => loadStoredWeights())

  useEffect(() => {
    return onWeightsChange((next) => {
      setWeights(next)
    })
  }, [])

  useEffect(() => {
    if ((panelOpen || weights) && !breakdown) {
      loadBreakdown().then(setBreakdown).catch(() => {})
    }
  }, [panelOpen, weights, breakdown])

  const isCustom = weights && sharesDiffer(weights, DEFAULT_WEIGHTS)

  const customScores = useMemo(() => {
    if (!isCustom || !breakdown) return null
    return Object.fromEntries(
      breakdown.technologies.map((t) => [t.slug, scoreFor(t.components, weights)]),
    )
  }, [isCustom, breakdown, weights])

  const itemsWithScores = useMemo(() => {
    const raw = data?.items ?? []
    if (!customScores) return raw
    return raw.map((t) => ({
      ...t,
      devintel_score: customScores[t.slug] ?? t.devintel_score,
      is_custom_score: customScores[t.slug] != null,
    }))
  }, [data, customScores])

  // The rank always means "position by score", whatever the list is sorted by
  const rankOf = useMemo(() => {
    const byScore = [...itemsWithScores].sort(SORTS.score[1])
    return new Map(byScore.map((t, i) => [t.slug, i + 1]))
  }, [itemsWithScores])

  const shown = useMemo(
    () =>
      itemsWithScores
        .filter((t) => (category === 'all' || t.category === category) && t.name.toLowerCase().includes(query.trim().toLowerCase()))
        .sort(SORTS[sort][1]),
    [itemsWithScores, category, query, sort],
  )

  const pages = Math.max(1, Math.ceil(shown.length / PAGE_SIZE))
  const current = Math.min(page, pages)
  const slice = shown.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE)
  const emerging = data?.emerging ?? []
  const categories = data?.categories ?? []

  function change(setter) {
    return (value) => { setter(value); setPage(1) }
  }

  return (
    <Page kicker="Page 01" title="Rankings" intro="Every tracked technology, scored from 0 to 100 by combining GitHub, Stack Overflow, Hacker News and job-post activity. Select a row to see the numbers behind its score.">
      <div className="di-split">
        <section className="di-panel" aria-label="Technology ranking">
          <div className="di-controls">
            <input
              type="search" className="di-input" value={query} placeholder="Search technologies, for example react"
              aria-label="Search technologies" onChange={(e) => change(setQuery)(e.target.value)}
            />
            <div className="di-filter" style={{ margin: 0 }} role="group" aria-label="Filter by category">
              {['all', ...categories].map((c) => (
                <button key={c} type="button" className="di-btn di-btn--sm" aria-pressed={category === c} onClick={() => change(setCategory)(c)}>
                  {c === 'all' ? 'All' : categoryName(c)}
                </button>
              ))}
            </div>
            <div className="di-controls__row">
              <label htmlFor="di-sort" style={{ fontWeight: 700 }}>Sort by</label>
              <select id="di-sort" className="di-select" value={sort} onChange={(e) => change(setSort)(e.target.value)}>
                {Object.entries(SORTS).map(([key, [label]]) => <option key={key} value={key}>{label}</option>)}
              </select>
              <button
                type="button"
                className={`di-btn di-btn--sm ${isCustom ? 'di-btn--lime' : ''}`}
                onClick={() => setPanelOpen(!panelOpen)}
                aria-expanded={panelOpen}
                style={{ marginLeft: 'auto' }}
              >
                ⚙️ {panelOpen ? 'Close weight sliders' : isCustom ? 'Custom weights active' : 'Customize weights'}
              </button>
            </div>
          </div>

          {panelOpen && (
            <div style={{ marginBottom: 20 }}>
              <WeightCustomizer showBar={true} onClose={() => setPanelOpen(false)} />
            </div>
          )}

          {isCustom && !panelOpen && (
            <div className="di-alert" style={{ background: 'var(--di-sun)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10, margin: '14px 0', border: '3px solid #000' }}>
              <span>⚡ <b>Custom scoring active:</b> Technologies are re-ranked using your custom signal weights.</span>
              <div style={{ display: 'flex', gap: 8 }}>
                <button type="button" className="di-btn di-btn--sm" onClick={() => setPanelOpen(true)}>Adjust sliders</button>
                <button type="button" className="di-btn di-btn--sm" onClick={() => storeWeights(null)}>Reset to defaults</button>
              </div>
            </div>
          )}

          <p className="di-count" aria-live="polite">
            {shown.length === 0 ? 'No technologies to show' : `Showing ${(current - 1) * PAGE_SIZE + 1} to ${(current - 1) * PAGE_SIZE + slice.length} of ${shown.length}`}
          </p>
          <ol className="di-list">
            {slice.length === 0 ? (
              <li className="di-empty">
                {data?.items.length
                  ? 'Nothing matches. Clear the search or pick another category.'
                  : 'No scores yet. Run python run_pipeline.py in the backend folder to collect data.'}
              </li>
            ) : (
              slice.map((t) => <Row key={t.slug} rank={rankOf.get(t.slug)} tech={t} onSelect={onSelect} />)
            )}
          </ol>

          {pages > 1 && (
            <nav className="di-pager" aria-label="Pages">
              <button type="button" className="di-btn di-btn--sm" disabled={current === 1} onClick={() => setPage(current - 1)}>Previous</button>
              {pageList(pages, current).map((n, i) =>
                n === 'gap' ? (
                  <span key={`gap-${i}`} className="di-pager__gap" aria-hidden="true">...</span>
                ) : (
                  <button key={n} type="button" className="di-btn di-btn--sm" aria-current={n === current ? 'page' : undefined} aria-label={`Page ${n}`} onClick={() => setPage(n)}>{n}</button>
                ),
              )}
              <button type="button" className="di-btn di-btn--sm" disabled={current === pages} onClick={() => setPage(current + 1)}>Next</button>
            </nav>
          )}
        </section>

        <div className="di-sticky">
          <aside className="di-panel di-panel--hot" aria-labelledby="di-em-title">
            <h2 id="di-em-title">Taking off</h2>
            <p className="di-panel__hint">Technologies growing much faster than the rest over the last 30 days.</p>
            <ul className="di-list">
              {emerging.length === 0 ? (
                <li className="di-empty">Nothing flagged yet. Growth needs at least 7 days of collected data, and the pipeline adds a new day every morning.</li>
              ) : (
                emerging.map((t) => (
                  <li key={t.slug}>
                    <button type="button" className="di-row di-row--duo" onClick={() => onSelect(t.slug)}>
                      <span className="di-row__name">{t.name}</span>
                      <span className="di-growth di-growth--up">{growthText(t.growth_30d)}</span>
                    </button>
                  </li>
                ))
              )}
            </ul>
          </aside>
          <aside className="di-panel di-howto" style={{ marginTop: 0 }} aria-labelledby="di-how-title">
            <h2 id="di-how-title">How to read this</h2>
            <ul>
              <li><b>Score</b> ranks a technology against the others on seven signals. 100 is the top.</li>
              <li><b>Growth</b> is the change over 30 days. It shows n/a until enough history exists.</li>
              <li><b>Taking off</b> needs a score of 20+, growth of 15%+, agreement between sources, and a place in the top 20% by growth.</li>
            </ul>
          </aside>
        </div>
      </div>
    </Page>
  )
}

import { useEffect, useMemo, useState } from 'react'
import { loadBreakdown } from '../lib/api'
import { METRIC_LABELS, categoryName, growthText } from '../lib/format'
import { defaultWeights, loadStoredWeights, scoreFor, sharesDiffer, storeWeights } from '../lib/score'

function Chip({ active, onClick, children }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`press cursor-pointer border-[3px] border-ink px-3 py-0.5 font-bold shadow-brut-xs hover:bg-sun hover:text-ink ${
        active ? 'bg-ink text-white' : 'bg-white'
      }`}
    >
      {children}
    </button>
  )
}

function Row({ rank, tech, onSelect }) {
  const growth = growthText(tech.growth_30d)
  const growthStyle =
    growth == null ? 'opacity-55' : tech.growth_30d > 0 ? 'border-2 border-ink bg-mint px-1' : ''
  return (
    <li>
      <button
        type="button"
        onClick={() => onSelect(tech.slug)}
        className="press grid w-full cursor-pointer grid-cols-[2rem_1fr_4.4rem] items-center gap-x-3 gap-y-2 border-[3px] border-ink bg-white px-3 py-2.5 text-left shadow-brut-sm hover:bg-sun md:grid-cols-[2.4rem_minmax(0,1.2fr)_minmax(0,1.5fr)_4.6rem]"
      >
        <span className="font-display text-xl">{rank}</span>
        <span className="flex flex-wrap items-center gap-1.5 text-lg font-bold">
          {tech.name}
          <span className="border-2 border-ink bg-lilac px-1.5 text-xs font-bold">{categoryName(tech.category)}</span>
          {tech.is_emerging && <span className="border-2 border-ink bg-hot px-1.5 text-xs font-bold">Taking off</span>}
        </span>
        <span className="order-4 col-span-3 flex items-center gap-2.5 md:order-none md:col-span-1">
          <span className="h-5 flex-1 border-[3px] border-ink bg-white">
            <span
              className="block h-full border-r-[3px] border-ink bg-sky"
              style={{ width: `${Math.max(2, tech.devintel_score ?? 0)}%` }}
            />
          </span>
          <span className="min-w-9 text-right font-display text-lg">{Math.round(tech.devintel_score ?? 0)}</span>
        </span>
        <span
          className={`order-3 justify-self-end font-bold md:order-none ${growthStyle}`}
          title={growth == null ? 'Growth needs at least 7 days of collected history' : undefined}
        >
          {growth ?? 'n/a'}
        </span>
      </button>
    </li>
  )
}

function Sliders({ breakdown, weights, setWeights, onReset }) {
  const metrics = Object.keys(breakdown.weights).sort((a, b) => breakdown.weights[b] - breakdown.weights[a])
  const total = metrics.reduce((sum, m) => sum + (weights[m] ?? 0), 0)
  return (
    <div className="mb-4 border-[3px] border-ink bg-lilac p-4">
      <p className="mb-3 text-sm">
        Drag a slider to change how much a signal counts. The ranking updates instantly in your browser. Nothing is saved on the server.
      </p>
      <ul className="flex flex-col gap-3">
        {metrics.map((m) => (
          <li key={m} className="grid grid-cols-[1fr_auto] items-center gap-x-3 gap-y-1">
            <label htmlFor={`w-${m}`} className="text-sm font-bold">{METRIC_LABELS[m] ?? m}</label>
            <span className="text-right text-sm font-bold">{total ? Math.round((100 * (weights[m] ?? 0)) / total) : 0}%</span>
            <input id={`w-${m}`} type="range" min="0" max="40" step="1" value={weights[m] ?? 0}
              onChange={(e) => setWeights({ ...weights, [m]: Number(e.target.value) })}
              className="col-span-2 h-2 w-full cursor-pointer accent-black" />
          </li>
        ))}
      </ul>
      {total === 0 && <p className="mt-3 border-2 border-ink bg-hot p-2 text-sm font-bold" role="alert">Move at least one slider above zero.</p>}
      <button type="button" onClick={onReset} className="press mt-4 cursor-pointer border-[3px] border-ink bg-white px-4 py-1 font-bold shadow-brut-xs hover:bg-sun">
        Reset to the default weights
      </button>
    </div>
  )
}

export default function RankingCard({ items, categories, onSelect }) {
  const [category, setCategory] = useState('all')
  const [query, setQuery] = useState('')
  const [panelOpen, setPanelOpen] = useState(false)
  const [breakdown, setBreakdown] = useState(null)
  const [weights, setWeights] = useState(loadStoredWeights)   // null = default weights

  // The per-signal ranks are fetched only when someone opens the panel (or had saved custom weights before)
  useEffect(() => {
    if ((panelOpen || weights) && !breakdown) loadBreakdown().then(setBreakdown).catch(() => {})
  }, [panelOpen, weights, breakdown])

  const defaults = useMemo(() => (breakdown ? defaultWeights(breakdown.weights) : null), [breakdown])
  const current = weights && defaults && Object.keys(defaults).every((m) => m in weights) ? weights : defaults
  const custom = !!(breakdown && current && sharesDiffer(current, defaults))

  const customScores = useMemo(() => {
    if (!custom) return null
    return Object.fromEntries(breakdown.technologies.map((t) => [t.slug, scoreFor(t.components, current)]))
  }, [custom, breakdown, current])

  function changeWeights(next) {
    setWeights(next)
    storeWeights(sharesDiffer(next, defaults) ? next : null)
  }
  function reset() {
    setWeights(null)
    storeWeights(null)
  }

  const shown = useMemo(() => {
    let list = items
    if (customScores) {
      list = items
        .map((t) => ({ ...t, devintel_score: customScores[t.slug] ?? t.devintel_score }))
        .sort((a, b) => (b.devintel_score ?? 0) - (a.devintel_score ?? 0))
    }
    return list.filter(
      (t) => (category === 'all' || t.category === category) && t.name.toLowerCase().includes(query.toLowerCase()),
    )
  }, [items, customScores, category, query])

  return (
    <section className="border-[3px] border-ink bg-white p-5 shadow-brut" aria-labelledby="h-rank">
      <h2 id="h-rank" className="font-display text-3xl leading-tight">Most popular right now</h2>
      <p className="mb-4 text-[0.95rem]">
        Score from 0 to 100, combining GitHub, Stack Overflow and Hacker News activity. Select a row for details.
      </p>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <button type="button" aria-expanded={panelOpen} onClick={() => setPanelOpen(!panelOpen)}
          className="press cursor-pointer border-[3px] border-ink bg-sun px-4 py-1 font-bold shadow-brut-xs">
          {panelOpen ? 'Hide score settings' : 'Customize the score'}
        </button>
        {custom && (
          <span className="flex flex-wrap items-center gap-2 text-sm font-bold">
            <span className="border-2 border-ink bg-hot px-2">Custom ranking</span>
            <button type="button" onClick={reset} className="cursor-pointer underline decoration-2 underline-offset-2 hover:bg-sun">Reset</button>
          </span>
        )}
      </div>
      {panelOpen && (breakdown && breakdown.technologies.some((t) => Object.keys(t.components).length)
        ? <Sliders breakdown={breakdown} weights={current} setWeights={changeWeights} onReset={reset} />
        : <p className="mb-4 border-[3px] border-dashed border-ink p-3 text-sm">{breakdown ? 'Score details appear after the next pipeline run.' : 'Loading...'}</p>)}
      <div className="mb-4 flex flex-col gap-3">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search technologies, for example react"
          aria-label="Search technologies"
          className="w-full border-[3px] border-ink bg-white px-3 py-2.5 shadow-brut-sm"
        />
        <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by category">
          <Chip active={category === 'all'} onClick={() => setCategory('all')}>All</Chip>
          {categories.map((c) => (
            <Chip key={c} active={category === c} onClick={() => setCategory(c)}>{categoryName(c)}</Chip>
          ))}
        </div>
      </div>
      <ol className="flex flex-col gap-3">
        {shown.length === 0 ? (
          <li className="border-[3px] border-dashed border-ink p-4">
            {items.length
              ? 'Nothing matches. Clear the search or pick another category.'
              : 'No scores yet. Run python run_pipeline.py in the backend folder to collect data.'}
          </li>
        ) : (
          shown.map((t, i) => <Row key={t.slug} rank={i + 1} tech={t} onSelect={onSelect} />)
        )}
      </ol>
    </section>
  )
}

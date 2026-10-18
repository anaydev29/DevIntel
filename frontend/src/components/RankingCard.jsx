import { useMemo, useState } from 'react'
import { categoryName, growthText } from '../lib/format'

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

export default function RankingCard({ items, categories, onSelect }) {
  const [category, setCategory] = useState('all')
  const [query, setQuery] = useState('')

  const shown = useMemo(
    () =>
      items.filter(
        (t) =>
          (category === 'all' || t.category === category) &&
          t.name.toLowerCase().includes(query.toLowerCase()),
      ),
    [items, category, query],
  )

  return (
    <section className="border-[3px] border-ink bg-white p-5 shadow-brut" aria-labelledby="h-rank">
      <h2 id="h-rank" className="font-display text-3xl leading-tight">Most popular right now</h2>
      <p className="mb-4 text-[0.95rem]">
        Score from 0 to 100, combining GitHub, Stack Overflow and Hacker News activity. Select a row for details.
      </p>
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

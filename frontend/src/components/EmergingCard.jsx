import { growthText } from '../lib/format'

export default function EmergingCard({ rows, onSelect }) {
  return (
    <aside className="border-[3px] border-ink bg-hot p-5 shadow-brut" aria-labelledby="h-em">
      <h2 id="h-em" className="font-display text-3xl leading-tight">Taking off</h2>
      <p className="mb-4 text-[0.95rem]">Technologies growing much faster than the rest over the last 30 days.</p>
      <ul className="flex flex-col gap-3">
        {rows.length === 0 ? (
          <li className="border-[3px] border-dashed border-ink bg-white p-4">
            Nothing flagged yet. Growth needs at least 7 days of collected data, and the pipeline adds a new day every morning.
          </li>
        ) : (
          rows.map((t) => (
            <li key={t.slug}>
              <button
                type="button"
                onClick={() => onSelect(t.slug)}
                className="press flex w-full cursor-pointer justify-between gap-4 border-[3px] border-ink bg-white px-3 py-2.5 font-bold shadow-brut-sm hover:bg-sun"
              >
                <span>{t.name}</span>
                <span>{growthText(t.growth_30d)}</span>
              </button>
            </li>
          ))
        )}
      </ul>
    </aside>
  )
}

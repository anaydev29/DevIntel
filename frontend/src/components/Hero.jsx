import { timeAgo } from '../lib/format'

const STATUS_COLOR = { success: 'bg-mint', partial: 'bg-sun', failed: 'bg-hot' }

function Sticker({ children, color = 'bg-white' }) {
  return (
    <span className={`border-[3px] border-ink px-3 py-0.5 text-sm font-bold shadow-brut-xs ${color}`}>
      {children}
    </span>
  )
}

export default function Hero({ count, runs }) {
  // runs arrive newest first, so the first run per source is its latest
  const latest = [...new Map([...runs].reverse().map((r) => [r.source, r])).values()]
  return (
    <header className="pt-4 md:pt-10">
      <h1 className="font-display text-[clamp(3.2rem,11vw,7.5rem)] leading-[0.9] tracking-tight">
        <span className="inline-block -rotate-[1.5deg] border-[3px] border-ink bg-sun px-[0.15em] shadow-brut">
          DevIntel
        </span>
      </h1>
      <p className="mt-6 mb-4 max-w-xl text-[clamp(1.1rem,2.2vw,1.45rem)] font-bold">
        See which technologies developers use most, and which ones are taking off.
      </p>
      <div className="flex flex-wrap gap-2.5" aria-live="polite">
        <Sticker>{count} technologies tracked</Sticker>
        {latest.map((r) => (
          <Sticker key={r.source} color={STATUS_COLOR[r.status] ?? 'bg-hot'}>
            {r.source} updated {timeAgo(r.started_at)}
          </Sticker>
        ))}
      </div>
    </header>
  )
}

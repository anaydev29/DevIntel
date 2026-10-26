import { useState } from 'react'
import { loadBacktest } from '../lib/api'
import { techLink } from '../lib/route'
import { useAsync } from '../lib/useAsync'

const card = 'border-[3px] border-ink bg-white p-5 shadow-brut'
const pct = (x, digits = 0) => `${(x * 100).toFixed(digits)}%`
const signed = (x) => `${x >= 0 ? '+' : ''}${(x * 100).toFixed(1)}%`

function verdict(r) {
  if (r.ci_low > r.baseline) return { text: 'Better than a random pick, even allowing for uncertainty.', color: 'bg-mint' }
  if (r.ci_high < r.baseline) return { text: 'Worse than a random pick. The flag needs rethinking.', color: 'bg-hot' }
  return { text: 'Not yet clearly different from a random pick. There are too few flags to tell, and more data will settle it.', color: 'bg-sun' }
}

export default function BacktestPage() {
  const [horizon, setHorizon] = useState(14)
  const state = useAsync(() => loadBacktest(horizon), [horizon])
  const r = state.data
  const v = r?.status === 'ready' ? verdict(r) : null

  return (
    <div className="flex max-w-4xl flex-col gap-8">
      <section className={card}>
        <h2 className="font-display text-3xl leading-tight">Does the "Taking off" flag work?</h2>
        <p className="mt-2">
          A flag is only useful if flagged technologies really keep growing. So we check our own past flags: for each one, we look at what happened
          in the days after, and compare it with the typical technology over the same days. A random pick would be right about half the time.
        </p>
        <div className="my-4 flex flex-wrap items-center gap-2" role="group" aria-label="How many days ahead to look">
          <span className="font-bold">Look ahead:</span>
          {[7, 14, 30].map((d) => (
            <button key={d} type="button" aria-pressed={horizon === d} onClick={() => setHorizon(d)}
              className={`press cursor-pointer border-[3px] border-ink px-3 py-0.5 font-bold shadow-brut-xs hover:bg-sun hover:text-ink ${horizon === d ? 'bg-ink text-white' : 'bg-white'}`}>{d} days</button>
          ))}
        </div>
        {state.loading && <p>Loading...</p>}
        {state.error && <p className="border-[3px] border-ink bg-hot p-3 font-bold">Could not load the results. Check that the API is running.</p>}
        {r && r.status !== 'ready' && <p className="border-[3px] border-dashed border-ink p-4">{r.message}</p>}
        {v && (
          <div className="border-[3px] border-ink p-4 shadow-brut-sm">
            <p className="font-display text-5xl leading-none">{pct(r.hit_rate)}</p>
            <p className="mt-2 text-lg font-bold">{r.hits} of {r.flags} flagged technologies grew faster than the typical technology over the next {r.horizon_days} days.</p>
            <p className="mt-1">A random pick would score about {pct(r.baseline)}. With only {r.flags} {r.flags === 1 ? 'flag' : 'flags'}, the true rate is probably between {pct(r.ci_low)} and {pct(r.ci_high)}.</p>
            <p className={`mt-3 border-2 border-ink p-2 font-bold ${v.color}`}>{v.text}</p>
            <p className="mt-3 text-sm">
              On average flagged technologies grew {signed(r.avg_forward_growth_flagged)}, while the average technology grew {signed(r.avg_forward_growth_all)}.
              Data up to {new Date(r.latest_data_date).toLocaleDateString('en', { day: 'numeric', month: 'short', year: 'numeric' })}.
            </p>
          </div>
        )}
      </section>

      {r?.events.length > 0 && (
        <section className={card}>
          <h3 className="font-display text-2xl leading-tight">Every flag we could judge</h3>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full border-collapse text-left text-sm">
              <thead><tr className="border-b-[3px] border-ink"><th className="py-2 pr-3">Technology</th><th className="pr-3">Flagged on</th><th className="pr-3">Grew</th><th className="pr-3">Typical</th><th>Result</th></tr></thead>
              <tbody>
                {r.events.map((e) => (
                  <tr key={`${e.slug}-${e.flagged_on}`} className="border-b-2 border-ink">
                    <td className="py-2 pr-3 font-bold"><a href={techLink(e.slug)} className="underline decoration-2 underline-offset-2 hover:bg-sun">{e.technology}</a></td>
                    <td className="pr-3">{new Date(e.flagged_on).toLocaleDateString('en', { day: 'numeric', month: 'short' })}</td>
                    <td className="pr-3">{signed(e.forward_growth)}</td>
                    <td className="pr-3">{signed(e.median_growth)}</td>
                    <td><span className={`border-2 border-ink px-2 font-bold ${e.beat_median ? 'bg-mint' : 'bg-white'}`}>{e.beat_median ? 'Beat typical' : 'Did not'}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section className={card}>
        <h3 className="font-display text-2xl leading-tight">How this is measured, and its limits</h3>
        <ul className="mt-2 list-disc pl-5">
          <li><b>Forward growth</b> is the weighted change in GitHub repositories, Stack Overflow questions, Wikipedia views and Hacker News stories from the flag day to {horizon} days later. The flag itself only used data from before that day.</li>
          <li>A flag is a <b>hit</b> if the technology grew faster than the <b>median</b> technology over the same days. Half of all technologies do, so a random pick scores about 50%.</li>
          <li>The same technology flagged on several days in a row counts <b>once</b> per {horizon}-day window.</li>
          <li><b>Few flags means an uncertain result.</b> The range shown is a 95% interval, and it is wide until many flags have been judged.</li>
          <li>Growth is measured with the same kinds of signals that raise the flag, so a technology can look good partly because of how both are defined. The real test is how the result holds up as months of data accumulate.</li>
        </ul>
      </section>
    </div>
  )
}

import { useState } from 'react'
import { loadHistory, loadTechPage, loadTopics } from '../lib/api'
import { METRIC_LABELS, categoryName, compact, formatMetric, growthText, timeAgo } from '../lib/format'
import { goHome, newTopicLink, techLink, topicLink } from '../lib/route'
import { useAsync } from '../lib/useAsync'
import DiscussionPanel from './DiscussionPanel'
import LineChart from './LineChart'
import ScoreBreakdown from './ScoreBreakdown'
import WatchButton from './WatchButton'

const card = 'border-[3px] border-ink bg-white p-5 shadow-brut'
const linkClass = 'font-bold underline decoration-2 underline-offset-4 hover:bg-sun'

function Sticker({ children, color = 'bg-white' }) {
  return <span className={`border-[3px] border-ink px-3 py-0.5 font-bold shadow-brut-xs ${color}`}>{children}</span>
}

function Trends({ slug, name }) {
  const history = useAsync(() => loadHistory(slug), [slug])
  const [metric, setMetric] = useState('')
  const h = history.data
  if (!h) return null
  const available = Object.keys(METRIC_LABELS).filter((m) => h.metrics[m]?.length)
  const chosen = metric && h.metrics[metric] ? metric : (available.includes('stackoverflow.questions_30d') ? 'stackoverflow.questions_30d' : available[0])
  return (
    <section className={card}>
      <h3 className="font-display text-2xl leading-tight">Trends</h3>
      <p className="mb-3 text-sm">How {name} has moved since we started collecting. One point is added every day.</p>
      <h4 className="mb-2 font-bold">DevIntel Score</h4>
      <LineChart label={`DevIntel Score of ${name} over time`} domain={[0, 100]}
        series={[{ name: 'Score', color: '#4D7CFF', points: h.score.map((p) => ({ date: p.date, value: p.value })) }]} />
      {chosen && (
        <div className="mt-6">
          <label className="mb-2 flex flex-wrap items-center gap-3 font-bold">
            Signal
            <select value={chosen} onChange={(e) => setMetric(e.target.value)} className="cursor-pointer border-[3px] border-ink bg-white px-3 py-1 shadow-brut-xs">
              {available.map((m) => <option key={m} value={m}>{METRIC_LABELS[m]}</option>)}
            </select>
          </label>
          <LineChart label={`${METRIC_LABELS[chosen]} of ${name} over time`} formatY={(v) => formatMetric(chosen, v)}
            series={[{ name: METRIC_LABELS[chosen], color: '#FF5CA8', points: h.metrics[chosen] }]} />
        </div>
      )}
    </section>
  )
}

export default function TechnologyPage({ slug }) {
  const page = useAsync(() => loadTechPage(slug), [slug])
  const topics = useAsync(() => loadTopics(slug, 'active', 5).catch(() => []), [slug])
  const p = page.data
  const t = p?.technology

  return (
    <div className="flex flex-col gap-8">
      <button type="button" onClick={goHome} className="w-fit cursor-pointer text-sm font-bold underline decoration-2 underline-offset-4 hover:bg-sun">Back to rankings</button>
      {page.loading && <p className={card}>Loading...</p>}
      {page.error && <p className={`${card} bg-hot font-bold`}>This technology was not found.</p>}
      {t && (
        <>
          <section className={card}>
            <h2 className="font-display text-4xl leading-tight">{t.name}</h2>
            <div className="my-3 flex flex-wrap gap-3">
              <Sticker>{categoryName(t.category)}</Sticker>
              {t.devintel_score != null && <Sticker>Score {Math.round(t.devintel_score)} of 100</Sticker>}
              <Sticker color={t.is_emerging ? 'bg-hot' : 'bg-white'}>{growthText(t.growth_30d) ? `30-day growth ${growthText(t.growth_30d)}` : 'Growth needs 7 days of data'}</Sticker>
            </div>
            <dl className="grid gap-2">
              {Object.entries(METRIC_LABELS).filter(([k]) => t.latest_metrics[k] != null).map(([k, label]) => (
                <div key={k} className="flex justify-between gap-4 border-b-2 border-ink pb-1.5"><dt>{label}</dt><dd className="font-bold">{formatMetric(k, t.latest_metrics[k])}</dd></div>
              ))}
            </dl>
            {t.aliases.length > 0 && <p className="mt-3 text-sm">Also known as: {t.aliases.join(', ')}</p>}
            <div className="mt-4"><WatchButton slug={t.slug} /></div>
            <ScoreBreakdown slug={t.slug} />
          </section>

          <Trends slug={t.slug} name={t.name} />

          <section className={card}>
            <h3 className="font-display text-2xl leading-tight">Related technologies</h3>
            <p className="mb-3 text-sm">Technologies that often appear in the same recent articles.</p>
            {p.related.length === 0 ? <p className="border-[3px] border-dashed border-ink p-3">Nothing to show yet. This fills in as more articles are collected.</p> : (
              <div className="flex flex-wrap gap-3">
                {p.related.map((r) => (
                  <a key={r.slug} href={techLink(r.slug)} className="press border-[3px] border-ink bg-lilac px-3 py-1 font-bold shadow-brut-xs hover:bg-sun">
                    {r.name} <span className="text-sm font-normal">({r.together} {r.together === 1 ? 'article' : 'articles'})</span>
                  </a>
                ))}
              </div>
            )}
          </section>

          <section className={card}>
            <h3 className="font-display text-2xl leading-tight">Learn {t.name}</h3>
            <p className="mb-3 text-sm">Popular recent dev.to articles, beginner-friendly ones first.</p>
            {p.articles.length === 0 ? <p className="border-[3px] border-dashed border-ink p-3">No articles collected yet.</p> : (
              <ul className="flex flex-col gap-3">
                {p.articles.map((a) => (
                  <li key={a.id} className="border-[3px] border-ink p-3 shadow-brut-xs">
                    <a href={a.url} target="_blank" rel="noopener noreferrer" className={linkClass}>{a.title}</a>
                    <p className="mt-1 text-sm">{[a.author, a.reading_time && `${a.reading_time} min read`, `${compact.format(a.score)} reactions`].filter(Boolean).join(', ')}
                      {a.beginner && <span className="ml-2 border-2 border-ink bg-mint px-1.5 font-bold">Beginner friendly</span>}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className={card}>
            <h3 className="font-display text-2xl leading-tight">Popular repositories</h3>
            {p.repos.length === 0 ? <p className="mt-2 border-[3px] border-dashed border-ink p-3">No repositories collected yet.</p> : (
              <ul className="mt-3 flex flex-col gap-2">
                {p.repos.map((r) => (
                  <li key={r.full_name} className="flex flex-wrap items-center justify-between gap-2 border-2 border-ink p-2">
                    <a href={r.url} target="_blank" rel="noopener noreferrer" className={linkClass}>{r.full_name}</a>
                    <span className="text-sm">{compact.format(r.stars)} stars{r.language ? `, ${r.language}` : ''}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className={card}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h3 className="font-display text-2xl leading-tight">Topics about {t.name}</h3>
              <a href={newTopicLink({ tech: t.slug })} className="press border-[3px] border-ink bg-sun px-4 py-1 font-bold shadow-brut-xs">Start a topic</a>
            </div>
            {(topics.data ?? []).length === 0 ? <p className="mt-3 border-[3px] border-dashed border-ink p-3">No topics yet.</p> : (
              <ul className="mt-3 flex flex-col gap-2">
                {topics.data.map((x) => (
                  <li key={x.ref} className="border-2 border-ink p-2">
                    <a href={topicLink(x.ref)} className={linkClass}>{x.title}</a>
                    <p className="text-sm">{x.replies} {x.replies === 1 ? 'reply' : 'replies'}, last activity {timeAgo(x.last_activity)}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className={card}>
            <h3 className="mb-3 font-display text-2xl leading-tight">Discussion</h3>
            <DiscussionPanel kind="technology" refKey={t.slug} />
          </section>
        </>
      )}
    </div>
  )
}

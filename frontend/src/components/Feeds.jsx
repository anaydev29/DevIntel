import { useMemo, useState } from 'react'
import { loadBlogs, loadNews, loadRepos } from '../lib/api'
import { compact, safeHref, timeAgo } from '../lib/format'
import { useAsync } from '../lib/useAsync'
import { useCounts } from '../lib/useCounts'
import { DiscussToggle } from './DiscussionPanel'
import { newTopicLink } from '../lib/route'

const cardClass = 'border-[3px] border-ink bg-white p-4 shadow-brut-sm'

function Stat({ color = 'bg-white', children }) {
  return <span className={`border-2 border-ink px-2 text-sm font-bold ${color}`}>{children}</span>
}

function Status({ state, empty, command }) {
  if (state.loading) return <p className={cardClass}>Loading...</p>
  if (state.error) return <p className={`${cardClass} bg-hot font-bold`}>Could not load this feed. Check that the API is running.</p>
  if (!state.data.length) {
    return (
      <p className="border-[3px] border-dashed border-ink bg-white p-4">
        {empty} Run <code className="font-bold">{command}</code> in the backend folder to collect it.
      </p>
    )
  }
  return null
}

function Panel({ title, hint, children }) {
  return (
    <section className="border-[3px] border-ink bg-white p-5 shadow-brut">
      <h2 className="font-display text-3xl leading-tight">{title}</h2>
      <p className="mb-4 text-[0.95rem]">{hint}</p>
      {children}
    </section>
  )
}

function ArticleCard({ a, scoreLabel, count = 0 }) {
  const host = (() => { try { return new URL(a.url).hostname.replace(/^www\./, '') } catch { return '' } })()
  return (
    <li className={cardClass}>
      <a href={safeHref(a.url)} target="_blank" rel="noopener noreferrer" className="text-lg font-bold underline decoration-2 underline-offset-4 hover:bg-sun">
        {a.title}
      </a>
      <p className="mt-1 text-sm">
        {[a.author, host && a.source === 'hackernews' ? host : null, a.published_at && timeAgo(a.published_at), a.reading_time && `${a.reading_time} min read`]
          .filter(Boolean).join(', ')}
      </p>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <Stat color="bg-mint">{compact.format(a.score)} {scoreLabel}</Stat>
        <Stat>{compact.format(a.comments)} comments</Stat>
        {a.discussion_url && (
          <a href={a.discussion_url} target="_blank" rel="noopener noreferrer" className="border-2 border-ink bg-sun px-2 text-sm font-bold hover:bg-white">
            HN thread
          </a>
        )}
        {a.tags.slice(0, 4).map((t) => <Stat key={t} color="bg-lilac">{t}</Stat>)}
      </div>
      <DiscussToggle kind="article" refKey={String(a.id)} initialCount={count}
        extra={<a href={newTopicLink({ articleId: a.id, about: a.title })} className="press border-2 border-ink bg-white px-2.5 py-0.5 text-sm font-bold hover:bg-sun">Start a topic about this</a>} />
    </li>
  )
}

export function BlogsPage({ technologies }) {
  const [tech, setTech] = useState('')
  const state = useAsync(() => loadBlogs(tech), [tech])
  const counts = useCounts('article', (state.data ?? []).map((a) => a.id))
  return (
    <Panel title="Blogs" hint="Most popular dev.to articles from the last two weeks.">
      <label className="mb-4 flex flex-wrap items-center gap-3 font-bold">
        Technology
        <select value={tech} onChange={(e) => setTech(e.target.value)} className="cursor-pointer border-[3px] border-ink bg-white px-3 py-2 shadow-brut-sm">
          <option value="">All technologies</option>
          {technologies.map((t) => <option key={t.slug} value={t.slug}>{t.name}</option>)}
        </select>
      </label>
      <Status state={state} empty="No articles yet." command="python run_pipeline.py --source devto" />
      {state.data?.length > 0 && <ul className="flex flex-col gap-3">{state.data.map((a) => <ArticleCard key={a.id} a={a} scoreLabel="reactions" count={counts[a.id] ?? 0} />)}</ul>}
    </Panel>
  )
}

export function NewsPage() {
  const state = useAsync(loadNews, [])
  const counts = useCounts('article', (state.data ?? []).map((a) => a.id))
  return (
    <Panel title="News" hint="What is on the Hacker News front page right now.">
      <Status state={state} empty="No news yet." command="python run_pipeline.py --source hn_frontpage" />
      {state.data?.length > 0 && <ul className="flex flex-col gap-3">{state.data.map((a) => <ArticleCard key={a.id} a={a} scoreLabel="points" count={counts[a.id] ?? 0} />)}</ul>}
    </Panel>
  )
}

export function ReposPage() {
  const state = useAsync(loadRepos, [])
  const counts = useCounts('repo', (state.data ?? []).map((r) => r.full_name))
  const [lang, setLang] = useState('all')
  const languages = useMemo(() => [...new Set((state.data ?? []).map((r) => r.language).filter(Boolean))].sort(), [state.data])
  const shown = (state.data ?? []).filter((r) => lang === 'all' || r.language === lang)
  return (
    <Panel title="Trending repositories" hint="The most-starred GitHub repositories created in the last 7 days.">
      {languages.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-2" role="group" aria-label="Filter by language">
          {['all', ...languages].map((l) => (
            <button key={l} type="button" aria-pressed={lang === l} onClick={() => setLang(l)}
              className={`press cursor-pointer border-[3px] border-ink px-3 py-0.5 font-bold shadow-brut-xs hover:bg-sun hover:text-ink ${lang === l ? 'bg-ink text-white' : 'bg-white'}`}>
              {l === 'all' ? 'All' : l}
            </button>
          ))}
        </div>
      )}
      <Status state={state} empty="No repositories yet." command="python run_pipeline.py --source github_trending" />
      {shown.length > 0 && (
        <ol className="flex flex-col gap-3">
          {shown.map((r, i) => (
            <li key={r.full_name} className={`${cardClass} grid grid-cols-[2rem_1fr] gap-3`}>
              <span className="font-display text-xl">{i + 1}</span>
              <div>
                <a href={r.url} target="_blank" rel="noopener noreferrer" className="text-lg font-bold underline decoration-2 underline-offset-4 hover:bg-sun">{r.full_name}</a>
                {r.description && <p className="mt-1">{r.description}</p>}
                <div className="mt-2 flex flex-wrap gap-2">
                  <Stat color="bg-sun">{compact.format(r.stars)} stars</Stat>
                  <Stat>{compact.format(r.forks)} forks</Stat>
                  {r.language && <Stat color="bg-lilac">{r.language}</Stat>}
                  {r.created_at && <Stat>created {timeAgo(r.created_at)}</Stat>}
                </div>
                <DiscussToggle kind="repo" refKey={r.full_name} initialCount={counts[r.full_name] ?? 0} />
              </div>
            </li>
          ))}
        </ol>
      )}
    </Panel>
  )
}

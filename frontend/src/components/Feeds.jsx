import { useMemo, useState } from 'react'
import { loadBlogs, loadNews, loadRepos } from '../lib/api'
import { compact, timeAgo } from '../lib/format'
import { useAsync } from '../lib/useAsync'
import Page from './Page'
import { DiscussToggle } from './DiscussionPanel'

function Status({ state, empty, command }) {
  if (state.loading) return <p className="di-empty">Loading...</p>
  if (state.error) return <p className="di-alert" style={{ margin: 0 }}>Could not load this feed. Check that the API is running.</p>
  if (!state.data.length) {
    return <p className="di-empty">{empty} Run <code style={{ fontWeight: 700 }}>{command}</code> in the backend folder to collect it.</p>
  }
  return null
}

const hostOf = (url) => {
  try { return new URL(url).hostname.replace(/^www\./, '') } catch { return '' }
}

export function NewsPage() {
  const state = useAsync(loadNews, [])
  return (
    <Page kicker="Page 05" title="News" intro="What is on the Hacker News front page right now, collected once a day.">
      <Status state={state} empty="No news yet." command="python run_pipeline.py --source hn_frontpage" />
      {state.data?.length > 0 && (
        <ol className="di-news">
          {state.data.map((a, i) => {
            const host = hostOf(a.url)
            return (
              <li key={a.id} className="di-card di-story di-lift">
                <span className="di-story__no">{i + 1}</span>
                <div>
                  <a href={a.url} target="_blank" rel="noopener noreferrer" className="di-story__title di-link-plain">{a.title}</a>
                  <p className="di-story__meta">
                    {host && <span className="di-chip bg-lilac">{host}</span>}
                    {a.author && <span>by {a.author}</span>}
                    {a.published_at && <span>{timeAgo(a.published_at)}</span>}
                    <span className="di-chip">{compact.format(a.comments)} comments</span>
                    {a.discussion_url && (
                      <a href={a.discussion_url} target="_blank" rel="noopener noreferrer" className="di-chip bg-sun" style={{ color: '#000' }}>HN thread</a>
                    )}
                  </p>
                  <DiscussToggle
                    kind="article"
                    refKey={String(a.id)}
                    initialCount={0}
                    extra={
                      <a
                        href={`#/topics/new?article=${encodeURIComponent(a.id)}&about=${encodeURIComponent(a.title)}`}
                        className="press border-2 border-ink bg-white px-2.5 py-0.5 text-xs font-bold hover:bg-sun"
                      >
                        Start a topic
                      </a>
                    }
                  />
                </div>
                <div className="di-points"><b>{compact.format(a.score)}</b><span>points</span></div>
              </li>
            )
          })}
        </ol>
      )}
    </Page>
  )
}

export function BlogsPage({ technologies }) {
  const [tech, setTech] = useState('')
  const state = useAsync(() => loadBlogs(tech), [tech])
  return (
    <Page kicker="Page 06" title="Blogs" intro="The most popular Dev.to articles from the last two weeks.">
      <div className="di-controls__row" style={{ marginBottom: 22 }}>
        <label htmlFor="di-blog-tech" style={{ fontWeight: 700 }}>Technology</label>
        <select id="di-blog-tech" className="di-select" value={tech} onChange={(e) => setTech(e.target.value)}>
          <option value="">All technologies</option>
          {technologies.map((t) => <option key={t.slug} value={t.slug}>{t.name}</option>)}
        </select>
      </div>
      <Status state={state} empty="No articles yet." command="python run_pipeline.py --source devto" />
      {state.data?.length > 0 && (
        <ul className="di-grid2">
          {state.data.map((a) => (
            <li key={a.id}>
              <article className="di-card di-post di-lift">
                {a.tags.length > 0 && (
                  <div className="di-tags">{a.tags.slice(0, 4).map((t) => <span key={t} className="di-chip bg-lilac">#{t}</span>)}</div>
                )}
                <a href={a.url} target="_blank" rel="noopener noreferrer" className="di-post__title di-link-plain">{a.title}</a>
                <p className="di-post__meta">
                  {[a.author, a.published_at && timeAgo(a.published_at), a.reading_time && `${a.reading_time} min read`].filter(Boolean).join(', ')}
                </p>
                <div className="di-post__foot">
                  <span className="di-chip bg-mint">{compact.format(a.score)} reactions</span>
                  <span className="di-chip">{compact.format(a.comments)} comments</span>
                </div>
                <DiscussToggle
                  kind="article"
                  refKey={String(a.id)}
                  initialCount={0}
                  extra={
                    <a
                      href={`#/topics/new?article=${encodeURIComponent(a.id)}&about=${encodeURIComponent(a.title)}`}
                      className="press border-2 border-ink bg-white px-2.5 py-0.5 text-xs font-bold hover:bg-sun"
                    >
                      Start a topic
                    </a>
                  }
                />
              </article>
            </li>
          ))}
        </ul>
      )}
    </Page>
  )
}

const LANG_COLORS = {
  Python: '#3572A5', JavaScript: '#F1E05A', TypeScript: '#3178C6', Go: '#00ADD8',
  Rust: '#DEA584', Java: '#B07219', 'C++': '#F34B7D', C: '#888888', 'C#': '#178600', Kotlin: '#A97BFF', Swift: '#F05138',
}

export function ReposPage() {
  const state = useAsync(loadRepos, [])
  const [lang, setLang] = useState('all')
  const languages = useMemo(() => [...new Set((state.data ?? []).map((r) => r.language).filter(Boolean))].sort(), [state.data])
  const shown = (state.data ?? []).filter((r) => lang === 'all' || r.language === lang)
  return (
    <Page kicker="Page 07" title="Trending repos" intro="The most-starred GitHub repositories created in the last 7 days. GitHub has no official trending list, so this is the closest honest approximation.">
      {languages.length > 0 && (
        <div className="di-filter" role="group" aria-label="Filter by language">
          {['all', ...languages].map((l) => (
            <button key={l} type="button" className="di-btn di-btn--sm" aria-pressed={lang === l} onClick={() => setLang(l)}>
              {l === 'all' ? 'All' : l}
            </button>
          ))}
        </div>
      )}
      <Status state={state} empty="No repositories yet." command="python run_pipeline.py --source github_trending" />
      {shown.length > 0 && (
        <ol className="di-grid2">
          {shown.map((r, i) => (
            <li key={r.full_name}>
              <article className="di-card di-repo di-lift">
                <span className={`di-rank di-rank--${i < 3 ? i + 1 : 'x'}`}>{i + 1}</span>
                <div>
                  <a href={r.url} target="_blank" rel="noopener noreferrer" className="di-repo__name di-link-plain">{r.full_name}</a>
                  {r.description && <p>{r.description}</p>}
                  <div className="di-post__foot">
                    <span className="di-chip bg-sun">{compact.format(r.stars)} stars</span>
                    <span className="di-chip">{compact.format(r.forks)} forks</span>
                    {r.language && (
                      <span className="di-chip di-lang"><i style={{ background: LANG_COLORS[r.language] ?? '#e6e2ff' }} />{r.language}</span>
                    )}
                    {r.created_at && <span className="di-chip">created {timeAgo(r.created_at)}</span>}
                  </div>
                  <DiscussToggle
                    kind="repo"
                    refKey={r.full_name}
                    initialCount={0}
                    extra={
                      <a
                        href={`#/topics/new?about=${encodeURIComponent(r.full_name)}`}
                        className="press border-2 border-ink bg-white px-2.5 py-0.5 text-xs font-bold hover:bg-sun"
                      >
                        Start a topic
                      </a>
                    }
                  />
                </div>
              </article>
            </li>
          ))}
        </ol>
      )}
    </Page>
  )
}

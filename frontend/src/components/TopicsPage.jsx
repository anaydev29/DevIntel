import { useState } from 'react'
import { createTopic, loadTopics } from '../lib/api'
import { useAuth } from '../lib/auth'
import { timeAgo } from '../lib/format'
import { newTopicLink, techLink, topicLink } from '../lib/route'
import { useAsync } from '../lib/useAsync'

const card = 'border-[3px] border-ink bg-white p-5 shadow-brut'
const field = 'w-full border-[3px] border-ink bg-white px-3 py-2'

function NewTopic({ technologies, route }) {
  const { authenticated, loginEnabled, banned } = useAuth()
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [tech, setTech] = useState(route.tech ?? '')
  const [articleId, setArticleId] = useState(route.articleId ?? null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  if (!authenticated) {
    return (
      <p className="border-[3px] border-dashed border-ink p-4">
        {loginEnabled ? <><a href="/auth/google/login" className="font-bold underline">Sign in with Google</a> to start a topic.</> : 'Sign-in is not set up on this server.'}
      </p>
    )
  }
  if (banned) return <p className="border-[3px] border-ink bg-hot p-4 font-bold">Your account is restricted: you can read, but not post.</p>

  async function submit() {
    setBusy(true)
    setError('')
    try {
      const t = await createTopic({ title, body, technology: tech || null, article_id: articleId ? Number(articleId) : null })
      window.location.hash = topicLink(t.ref).slice(1)
    } catch (e) {
      setError(e.message)
      setBusy(false)
    }
  }

  return (
    <div className="mb-6 flex flex-col gap-3 border-[3px] border-ink bg-lilac p-4">
      <h3 className="font-display text-xl">Start a topic</h3>
      {articleId && (
        <p className="border-2 border-ink bg-white p-2 text-sm">
          About the article: <b>{route.about || `article ${articleId}`}</b>{' '}
          <button type="button" className="underline" onClick={() => setArticleId(null)}>Remove</button>
        </p>
      )}
      <label className="font-bold" htmlFor="t-title">Title</label>
      <input id="t-title" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={120} placeholder="A clear question or idea, 5 to 120 characters" className={field} />
      <label className="font-bold" htmlFor="t-body">What do you want to discuss?</label>
      <textarea id="t-body" value={body} onChange={(e) => setBody(e.target.value)} rows={5} maxLength={2000} className={field} />
      <label className="font-bold" htmlFor="t-tech">About a technology (optional)</label>
      <select id="t-tech" value={tech} onChange={(e) => setTech(e.target.value)} className={`${field} cursor-pointer`}>
        <option value="">No specific technology</option>
        {technologies.map((t) => <option key={t.slug} value={t.slug}>{t.name}</option>)}
      </select>
      <p className="text-xs">Plain text only, at most 2 links, and your first name with last initial is shown. Please follow the community guidelines. You can start 5 topics a day.</p>
      {error && <p className="border-2 border-ink bg-hot p-2 text-sm font-bold" role="alert">{error}</p>}
      <div>
        <button type="button" disabled={busy || title.trim().length < 5 || !body.trim()} onClick={submit}
          className="press cursor-pointer border-[3px] border-ink bg-sun px-6 py-1.5 font-bold shadow-brut-sm disabled:cursor-not-allowed disabled:opacity-50">
          {busy ? 'Posting...' : 'Post topic'}
        </button>
      </div>
    </div>
  )
}

export default function TopicsPage({ technologies, route }) {
  const [sort, setSort] = useState('active')
  const [tech, setTech] = useState('')
  const state = useAsync(() => loadTopics(tech, sort), [tech, sort])
  const sortBtn = (value, label) => (
    <button type="button" aria-pressed={sort === value} onClick={() => setSort(value)}
      className={`press cursor-pointer border-[3px] border-ink px-3 py-0.5 font-bold shadow-brut-xs hover:bg-sun hover:text-ink ${sort === value ? 'bg-ink text-white' : 'bg-white'}`}>{label}</button>
  )

  return (
    <section className={card}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-3xl leading-tight">Topics</h2>
        {!route?.creating && <a href={newTopicLink()} className="press border-[3px] border-ink bg-sun px-5 py-1.5 font-bold shadow-brut-sm">Start a topic</a>}
      </div>
      <p className="mb-4 text-[0.95rem]">Ask a question or share an idea about any technology. Anyone can read; sign in to take part.</p>
      {route?.creating && <NewTopic technologies={technologies} route={route} />}

      <div className="mb-4 flex flex-wrap items-center gap-3">
        {sortBtn('active', 'Most active')}{sortBtn('new', 'Newest')}
        <select aria-label="Filter by technology" value={tech} onChange={(e) => setTech(e.target.value)} className="cursor-pointer border-[3px] border-ink bg-white px-3 py-1">
          <option value="">All technologies</option>
          {technologies.map((t) => <option key={t.slug} value={t.slug}>{t.name}</option>)}
        </select>
      </div>

      {state.loading && <p>Loading...</p>}
      {state.error && <p className="border-[3px] border-ink bg-hot p-3 font-bold">Could not load topics. Check that the API is running.</p>}
      {state.data && state.data.length === 0 && <p className="border-[3px] border-dashed border-ink p-4">No topics yet. Be the first to start one.</p>}
      <ul className="flex flex-col gap-3">
        {(state.data ?? []).map((t) => (
          <li key={t.ref} className="border-[3px] border-ink p-4 shadow-brut-xs">
            <a href={topicLink(t.ref)} className="text-lg font-bold underline decoration-2 underline-offset-4 hover:bg-sun">{t.title}</a>
            <p className="mt-1 text-sm">{t.author.name}, {timeAgo(t.created_at)}. {t.replies} {t.replies === 1 ? 'reply' : 'replies'}, last activity {timeAgo(t.last_activity)}.</p>
            <p className="mt-1 break-words">{t.preview}{t.preview.length >= 160 ? '...' : ''}</p>
            {(t.technology || t.article) && (
              <div className="mt-2 flex flex-wrap gap-2 text-sm font-bold">
                {t.technology && <a href={techLink(t.technology.slug)} className="border-2 border-ink bg-lilac px-2 hover:bg-sun">{t.technology.name}</a>}
                {t.article && <span className="border-2 border-ink px-2">About an article</span>}
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}

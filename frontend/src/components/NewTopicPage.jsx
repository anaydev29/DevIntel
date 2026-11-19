import { useState } from 'react'
import { createTopic } from '../lib/api'
import { useAuth } from '../lib/auth'

const field = 'w-full border-[3px] border-ink bg-white p-3'
const btn = 'border-[3px] border-ink bg-sun px-5 py-2 font-bold shadow-brut-xs hover:bg-lilac disabled:opacity-50'

export default function NewTopicPage({ tech, articleId, about }) {
  const { user, loginEnabled } = useAuth()
  const [title, setTitle] = useState(about ? `About: ${about}` : '')
  const [body, setBody] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  if (!user) {
    return (
      <div className="border-[3px] border-ink bg-white p-5 shadow-brut">
        <p className="font-bold">{loginEnabled ? 'Sign in to start a topic.' : 'Sign-in is not set up on this server.'}</p>
        {loginEnabled && <a href="/auth/google/login" className="mt-3 inline-block border-[3px] border-ink bg-lime px-4 py-1 font-bold shadow-brut-xs">Sign in with Google</a>}
      </div>
    )
  }

  async function submit(e) {
    e.preventDefault()
    setError(''); setSaving(true)
    try {
      const payload = { title, body }
      if (tech) payload.technology = tech
      if (articleId) payload.article_id = Number(articleId)
      const t = await createTopic(payload)
      window.location.hash = `/topic/${encodeURIComponent(t.ref)}`
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} className="flex max-w-2xl flex-col gap-4">
      {(tech || about) && (
        <p className="text-sm font-bold">
          This topic will be linked to {about ? <b>“{about}”</b> : null}{tech ? <> the technology <b>{tech}</b></> : null}.
        </p>
      )}
      <label className="flex flex-col gap-1">
        <span className="font-bold">Title (5–120 characters, no links)</span>
        <input className={field} value={title} onChange={(e) => setTitle(e.target.value)} maxLength={120} required />
      </label>
      <label className="flex flex-col gap-1">
        <span className="font-bold">Your post</span>
        <textarea className={field} rows={6} value={body} onChange={(e) => setBody(e.target.value)} required />
      </label>
      {error && <p className="border-[3px] border-ink bg-hot p-3 font-bold" role="alert">{error}</p>}
      <button type="submit" className={btn} disabled={saving}>{saving ? 'Posting…' : 'Start the topic'}</button>
    </form>
  )
}
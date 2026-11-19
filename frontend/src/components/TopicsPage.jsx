import { useEffect, useState } from 'react'
import { loadTopics } from '../lib/api'
import { newTopicLink, topicLink } from '../lib/route'
import { timeAgo } from '../lib/format'

const card = 'border-[3px] border-ink bg-white p-4 shadow-brut-xs'

export default function TopicsPage() {
  const [topics, setTopics] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    loadTopics().then(setTopics).catch((e) => setError(e.message))
  }, [])

  return (
    <div className="flex flex-col gap-6">
      <a href={newTopicLink()} className="w-fit border-[3px] border-ink bg-sun px-4 py-1 font-bold shadow-brut-xs hover:bg-lilac">Start a new topic</a>
      {error && <p className="border-[3px] border-ink bg-hot p-3 font-bold">{error}</p>}
      {!topics && !error && <p>Loading…</p>}
      {topics && topics.length === 0 && <p className="border-[3px] border-dashed border-ink p-4">No topics yet. Be the first to start one.</p>}
      {topics && topics.length > 0 && (
        <ul className="flex flex-col gap-3">
          {topics.map((t) => (
            <li key={t.ref} className={card}>
              <a href={topicLink(t.ref)} className="font-display text-xl font-bold underline decoration-2 underline-offset-4 hover:bg-sun">{t.title}</a>
              <p className="mt-1 text-sm">{t.preview}</p>
              <p className="mt-2 text-sm font-bold">
                {t.author.name} · {timeAgo(t.created_at)} · {t.replies} {t.replies === 1 ? 'reply' : 'replies'}
                {t.technology && <> · <a href={topicLink(t.ref)} className="border-2 border-ink bg-lilac px-1.5">{t.technology.name}</a></>}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
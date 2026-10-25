import { loadTopic } from '../lib/api'
import { timeAgo } from '../lib/format'
import { techLink } from '../lib/route'
import { useAsync } from '../lib/useAsync'
import DiscussionPanel from './DiscussionPanel'

export default function TopicPage({ refKey }) {
  const state = useAsync(() => loadTopic(refKey), [refKey])
  const t = state.data
  return (
    <section className="border-[3px] border-ink bg-white p-5 shadow-brut">
      <a href="#/topics" className="text-sm font-bold underline decoration-2 underline-offset-4 hover:bg-sun">Back to all topics</a>
      {state.loading && <p className="mt-4">Loading...</p>}
      {state.error && <p className="mt-4 border-[3px] border-ink bg-hot p-3 font-bold">This topic was removed or does not exist.</p>}
      {t && (
        <>
          <h2 className="mt-3 font-display text-3xl leading-tight">{t.title}</h2>
          <div className="my-3 flex flex-wrap items-center gap-2 text-sm font-bold">
            <span>{t.author.name}, {timeAgo(t.created_at)}</span>
            {t.technology && <a href={techLink(t.technology.slug)} className="border-2 border-ink bg-lilac px-2 hover:bg-sun">{t.technology.name}</a>}
            {t.article && <a href={t.article.url} target="_blank" rel="noopener noreferrer" className="border-2 border-ink bg-white px-2 underline hover:bg-sun">About: {t.article.title}</a>}
          </div>
          <div className="mt-4"><DiscussionPanel kind="general" refKey={t.ref} originalId={t.first_comment_id} /></div>
        </>
      )}
    </section>
  )
}

import { useEffect, useState } from 'react'
import { deleteComment, editComment, loadDiscussion, postComment, reportComment, voteComment } from '../lib/api'
import { useAuth } from '../lib/auth'
import { timeAgo } from '../lib/format'

const MAX = 2000
const btn = 'press cursor-pointer border-2 border-ink bg-white px-2.5 py-0.5 text-sm font-bold hover:bg-sun disabled:cursor-not-allowed disabled:opacity-50'
const REASONS = ['Spam', 'Abusive or rude', 'Off topic', 'Other']

function Composer({ placeholder, initial = '', submitLabel, onSubmit, onCancel }) {
  const [text, setText] = useState(initial)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit() {
    setBusy(true)
    setError('')
    try {
      await onSubmit(text)
      setText('')
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder={placeholder} rows={3} maxLength={MAX} aria-label={placeholder}
        className="w-full border-[3px] border-ink bg-white p-2.5" />
      <div className="flex flex-wrap items-center gap-3">
        <button type="button" disabled={busy || !text.trim()} onClick={submit} className={`${btn} bg-sun px-4 py-1`}>{busy ? 'Sending...' : submitLabel}</button>
        {onCancel && <button type="button" onClick={onCancel} className={btn}>Cancel</button>}
        <span className="text-xs">{text.length} / {MAX}. Plain text only; links are not clickable.</span>
      </div>
      {error && <p className="border-2 border-ink bg-hot px-2 py-1 text-sm font-bold" role="alert">{error}</p>}
    </div>
  )
}

function Comment({ c, depth, actions, state, setState, originalId }) {
  const { authenticated } = useAuth()
  const gone = c.status !== 'visible'
  const [mode, setMode] = useState(null) // reply / edit / report
  const [note, setNote] = useState('')

  return (
    <li className={depth ? 'border-l-[3px] border-ink pl-3' : ''}>
      <div className={`border-[3px] border-ink p-3 ${gone ? 'bg-lilac' : 'bg-white'}`}>
        <div className="mb-1 flex flex-wrap items-center gap-2 text-sm">
          {c.author && <span className="grid h-6 w-6 place-items-center border-2 border-ink bg-sun font-bold">{c.author.initial}</span>}
          <span className="font-bold">{c.author ? c.author.name : 'Removed'}</span>
          {c.id === originalId && <span className="border-2 border-ink bg-mint px-1.5 text-xs font-bold">Original post</span>}
          <span>{timeAgo(c.created_at)}{c.edited_at ? ' (edited)' : ''}</span>
        </div>
        {mode === 'edit' ? (
          <Composer initial={c.body} placeholder="Edit your comment" submitLabel="Save"
            onSubmit={async (t) => { setState(await actions.edit(c.id, t)); setMode(null) }} onCancel={() => setMode(null)} />
        ) : (
          <p className={`whitespace-pre-wrap break-words ${gone ? 'italic' : ''}`}>{c.body}</p>
        )}
        {!gone && mode !== 'edit' && (
          <div className="mt-2 flex flex-wrap gap-2">
            <button type="button" aria-pressed={c.voted} disabled={!authenticated || c.mine} onClick={async () => setState(await actions.vote(c))}
              title={!authenticated ? 'Sign in to vote' : c.mine ? 'You cannot vote on your own comment' : undefined}
              className={`${btn} ${c.voted ? 'bg-mint' : ''}`}>Upvote {c.score}</button>
            {authenticated && <button type="button" className={btn} onClick={() => setMode(mode === 'reply' ? null : 'reply')}>Reply</button>}
            {c.mine && <button type="button" className={btn} onClick={() => setMode('edit')}>Edit</button>}
            {c.mine && <button type="button" className={btn} onClick={async () => window.confirm('Delete this comment?') && setState(await actions.remove(c.id))}>Delete</button>}
            {authenticated && !c.mine && <button type="button" className={btn} onClick={() => setMode(mode === 'report' ? null : 'report')}>Report</button>}
          </div>
        )}
        {mode === 'reply' && (
          <div className="mt-3">
            <Composer placeholder="Write a reply" submitLabel="Reply" onSubmit={async (t) => { setState(await actions.post(t, c.id)); setMode(null) }} onCancel={() => setMode(null)} />
          </div>
        )}
        {mode === 'report' && (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            {REASONS.map((r) => (
              <button key={r} type="button" className={btn} onClick={async () => { await actions.report(c.id, r); setMode(null); setNote('Thanks, your report was sent.') }}>{r}</button>
            ))}
            <button type="button" className={btn} onClick={() => setMode(null)}>Cancel</button>
          </div>
        )}
        {note && <p className="mt-2 text-sm font-bold" role="status">{note}</p>}
      </div>
      {c.replies.length > 0 && (
        <ul className="mt-2 flex flex-col gap-2">
          {c.replies.map((r) => <Comment key={r.id} c={r} depth={1} actions={actions} state={state} setState={setState} originalId={originalId} />)}
        </ul>
      )}
    </li>
  )
}

export default function DiscussionPanel({ kind, refKey, onTotal, originalId }) {
  const { authenticated, loginEnabled, banned } = useAuth()
  const [state, setState] = useState(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    setState(null)
    loadDiscussion(kind, refKey).then((d) => !cancelled && setState(d)).catch(() => !cancelled && setError(true))
    return () => { cancelled = true }
  }, [kind, refKey])

  useEffect(() => { if (state && onTotal) onTotal(state.total) }, [state, onTotal])

  const actions = {
    post: (body, parentId) => postComment(kind, refKey, body, parentId),
    edit: (id, body) => editComment(id, body),
    remove: (id) => deleteComment(id),
    report: (id, reason) => reportComment(id, reason),
    vote: async (c) => {
      const res = await voteComment(c.id, !c.voted)
      const patch = (list) => list.map((x) => ({ ...x, ...(x.id === c.id ? { voted: res.voted, score: res.score } : {}), replies: patch(x.replies) }))
      return { ...state, comments: patch(state.comments) }
    },
  }

  if (error) return <p className="border-2 border-ink bg-hot p-2 font-bold">Could not load the discussion. Check that the API is running.</p>
  if (!state) return <p>Loading discussion...</p>

  return (
    <div className="flex flex-col gap-3">
      {authenticated && banned ? (
        <p className="border-[3px] border-ink bg-hot p-3 text-sm font-bold">Your account is restricted: you can read, but not post, vote or report.</p>
      ) : authenticated ? (
        <Composer placeholder="Join the discussion" submitLabel="Post comment" onSubmit={async (t) => setState(await actions.post(t, null))} />
      ) : (
        <p className="border-[3px] border-dashed border-ink p-3 text-sm">
          {loginEnabled ? <><a href="/auth/google/login" className="font-bold underline">Sign in with Google</a> to join the discussion.</> : 'Sign-in is not set up on this server.'}
        </p>
      )}
      {authenticated && !banned && <p className="text-xs">Your first name and last initial are shown with your comments. Please follow the community guidelines (linked at the bottom of the page); reported comments can be hidden.</p>}
      {state.comments.length === 0 ? (
        <p className="border-[3px] border-dashed border-ink p-3">No comments yet. Start the discussion.</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {state.comments.map((c) => <Comment key={c.id} c={c} depth={0} actions={actions} state={state} setState={setState} originalId={originalId} />)}
        </ul>
      )}
    </div>
  )
}

// "Discuss (3)" button that opens the discussion right under a card
export function DiscussToggle({ kind, refKey, initialCount = 0, extra = null }) {
  const [open, setOpen] = useState(false)
  const [count, setCount] = useState(initialCount)
  useEffect(() => setCount(initialCount), [initialCount])
  return (
    <div className="mt-3">
      <div className="flex flex-wrap items-center gap-3">
        <button type="button" aria-expanded={open} onClick={() => setOpen(!open)} className={`${btn} bg-sun`}>
          {open ? 'Hide discussion' : `Discuss (${count})`}
        </button>
        {extra}
      </div>
      {open && <div className="mt-3"><DiscussionPanel kind={kind} refKey={refKey} onTotal={setCount} /></div>}
    </div>
  )
}

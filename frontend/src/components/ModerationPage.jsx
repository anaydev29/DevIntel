import { useCallback, useEffect, useState } from 'react'
import { adminSetRole, adminUsers, modAction, modBan, modLog, modQueue, modUnban } from '../lib/api'
import { useAuth } from '../lib/auth'
import { timeAgo } from '../lib/format'

const card = 'border-[3px] border-ink bg-white p-5 shadow-brut'
const btn = 'press cursor-pointer border-2 border-ink bg-white px-3 py-1 text-sm font-bold hover:bg-sun disabled:cursor-not-allowed disabled:opacity-50'

function Case({ c, run }) {
  const [banning, setBanning] = useState(false)
  const [reason, setReason] = useState('')
  return (
    <li className="border-[3px] border-ink p-4 shadow-brut-xs">
      <div className="mb-2 flex flex-wrap items-center gap-2 text-sm">
        <span className={`border-2 border-ink px-2 font-bold ${c.status === 'hidden' ? 'bg-hot' : 'bg-lilac'}`}>
          {c.status === 'hidden' ? 'Auto-hidden' : 'Visible'}
        </span>
        <span className="font-bold">{c.author_name}</span>
        <span>(user {c.author_id}{c.author_banned ? ', banned' : ''})</span>
        <span>on {c.thread_kind}: {c.thread_ref}</span>
        <span>{timeAgo(c.created_at)}</span>
      </div>
      <p className="mb-3 whitespace-pre-wrap break-words border-2 border-ink bg-lilac p-3">{c.body}</p>
      <ul className="mb-3 list-disc pl-5 text-sm">
        {c.reports.map((r, i) => <li key={i}>{r.reason}, reported by {r.reporter} {timeAgo(r.created_at)}</li>)}
      </ul>
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" className={`${btn} bg-mint`} onClick={() => run(() => modAction(c.comment_id, 'restore'))}>Keep comment</button>
        <button type="button" className={`${btn} bg-hot`} onClick={() => run(() => modAction(c.comment_id, 'remove'))}>Remove comment</button>
        {!c.author_banned && <button type="button" className={btn} onClick={() => setBanning(!banning)}>Ban author</button>}
      </div>
      {banning && (
        <div className="mt-3 flex flex-wrap gap-2">
          <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason (kept in the log)" aria-label="Ban reason"
            className="w-full max-w-sm border-2 border-ink px-2 py-1" />
          <button type="button" className={`${btn} bg-hot`} onClick={() => run(async () => { await modBan(c.author_id, reason); setBanning(false) })}>Confirm ban</button>
        </div>
      )}
    </li>
  )
}

function People({ run, users, reload }) {
  return (
    <section className={card}>
      <h2 className="font-display text-2xl leading-tight">People (admin)</h2>
      <p className="mb-3 text-sm">Appoint moderators and manage bans. Admins are set in the server settings.</p>
      <ul className="flex flex-col gap-2">
        {users.map((u) => (
          <li key={u.id} className="flex flex-wrap items-center justify-between gap-2 border-2 border-ink p-2 text-sm">
            <span><b>{u.name || 'No name'}</b> ({u.email}), {u.role}{u.banned ? ', banned' : ''}</span>
            {u.role !== 'admin' && (
              <span className="flex gap-2">
                <button type="button" className={btn} onClick={() => run(() => adminSetRole(u.id, u.role === 'moderator' ? 'user' : 'moderator'), reload)}>
                  {u.role === 'moderator' ? 'Remove moderator' : 'Make moderator'}
                </button>
                <button type="button" className={btn} onClick={() => run(() => (u.banned ? modUnban(u.id) : modBan(u.id, 'banned by admin')), reload)}>
                  {u.banned ? 'Unban' : 'Ban'}
                </button>
              </span>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}

export default function ModerationPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [queue, setQueue] = useState(null)
  const [log, setLog] = useState([])
  const [users, setUsers] = useState([])
  const [error, setError] = useState('')

  const reload = useCallback(async () => {
    try {
      const [q, l] = await Promise.all([modQueue(), modLog()])
      setQueue(q); setLog(l)
      if (isAdmin) setUsers(await adminUsers())
    } catch (e) { setError(e.message) }
  }, [isAdmin])

  useEffect(() => { reload() }, [reload])

  async function run(action, after = reload) {
    setError('')
    try { await action(); await after() } catch (e) { setError(e.message) }
  }

  if (error && !queue) return <p className={`${card} bg-hot font-bold`}>{error}</p>
  if (!queue) return <p className={card}>Loading...</p>

  return (
    <div className="flex flex-col gap-8">
      <section className={card}>
        <h2 className="font-display text-3xl leading-tight">Moderation queue</h2>
        <p className="mb-4 text-sm">Reported comments waiting for a decision. "Keep" shows a hidden comment again; "Remove" takes it down. Both close the reports and are recorded in the log below.</p>
        {error && <p className="mb-3 border-2 border-ink bg-hot p-2 font-bold" role="alert">{error}</p>}
        {queue.length === 0 ? (
          <p className="border-[3px] border-dashed border-ink p-4">Nothing to review. Reported comments will show up here.</p>
        ) : (
          <ul className="flex flex-col gap-4">{queue.map((c) => <Case key={c.comment_id} c={c} run={run} />)}</ul>
        )}
      </section>

      {isAdmin && <People run={run} users={users} reload={reload} />}

      <section className={card}>
        <h2 className="font-display text-2xl leading-tight">Recent actions</h2>
        {log.length === 0 ? <p className="mt-2 text-sm">No moderator actions yet.</p> : (
          <ul className="mt-3 flex flex-col gap-1 text-sm">
            {log.map((e) => (
              <li key={e.id} className="border-b-2 border-ink pb-1">
                <b>{e.moderator}</b> {e.action}
                {e.comment_id ? ` comment ${e.comment_id}` : ''}{e.target_user_id ? ` user ${e.target_user_id}` : ''}
                {e.note ? `, note: ${e.note}` : ''} ({timeAgo(e.created_at)})
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

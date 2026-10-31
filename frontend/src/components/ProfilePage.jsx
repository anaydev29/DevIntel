import { useEffect, useRef, useState } from 'react'
import { deleteAccount, removeFromWatchlist, saveGithubUsername, saveSkills } from '../lib/api'
import { categoryName, growthText } from '../lib/format'
import { useAuth } from '../lib/auth'
import SkillPicker from './SkillPicker'

const card = 'border-[3px] border-ink bg-white p-5 shadow-brut'
const btn = 'press cursor-pointer border-[3px] border-ink px-5 py-1.5 font-bold shadow-brut-sm disabled:cursor-not-allowed disabled:opacity-50'

export default function ProfilePage({ technologies, onSelect }) {
  const { loading, user, loginEnabled, profile, setProfile } = useAuth()
  const [picked, setPicked] = useState(new Set())
  const [github, setGithub] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const loaded = useRef(false)

  useEffect(() => {
    if (profile && !loaded.current) {
      loaded.current = true
      setPicked(new Set(profile.skills))
      setGithub(profile.user.github_username ?? '')
    }
  }, [profile])

  const toggle = (slug) => setPicked((prev) => {
    const next = new Set(prev)
    next.has(slug) ? next.delete(slug) : next.add(slug)
    return next
  })

  async function run(action, doneMessage) {
    setBusy(true)
    setNotice('')
    try {
      await action()
      setNotice(doneMessage)
    } catch (e) {
      setNotice(e.message)
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <section className={card}><p>Loading...</p></section>

  if (!user) {
    return (
      <section className={card}>
        <h2 className="font-display text-3xl leading-tight">My profile</h2>
        <p className="mt-2 mb-4">Sign in to save your skills, keep a watchlist of technologies and, soon, join discussions. Browsing the rest of DevIntel never needs an account.</p>
        {loginEnabled
          ? <a href="/auth/google/login" className={`${btn} inline-block bg-sun`}>Sign in with Google</a>
          : <p className="border-[3px] border-dashed border-ink p-4">Sign-in is not set up on this server yet.</p>}
      </section>
    )
  }

  const me = profile?.user ?? user
  return (
    <div className="flex flex-col gap-8">
      <section className={card}>
        <h2 className="font-display text-3xl leading-tight">{me.name || 'My profile'}</h2>
        <p className="mb-4 text-sm">{me.email}. Only you can see this.</p>
        <label className="mb-1 block font-bold" htmlFor="gh">GitHub username (used to pre-fill the Skill gap tab)</label>
        <div className="flex flex-wrap gap-3">
          <input id="gh" value={github} onChange={(e) => setGithub(e.target.value)} placeholder="for example octocat"
            className="w-full max-w-xs border-[3px] border-ink bg-white px-3 py-2 shadow-brut-sm" />
          <button type="button" disabled={busy} className={`${btn} bg-sun`}
            onClick={() => run(async () => { const res = await saveGithubUsername(github); setProfile(res); setGithub(res.user.github_username ?? '') }, 'GitHub username saved')}>Save</button>
        </div>
      </section>

      <section className={card}>
        <h2 className="font-display text-2xl leading-tight">My skills</h2>
        <p className="mb-4 text-sm">The technologies you already know. They pre-fill the Skill gap tab.</p>
        <SkillPicker technologies={technologies} picked={picked} onToggle={toggle} />
        <button type="button" disabled={busy} className={`${btn} mt-5 bg-sun`}
          onClick={() => run(async () => { await saveSkills([...picked]); setProfile({ ...profile, skills: [...picked] }) }, 'Skills saved')}>
          Save skills
        </button>
      </section>

      <section className={card}>
        <h2 className="font-display text-2xl leading-tight">My watchlist</h2>
        {!profile?.watchlist?.length ? (
          <p className="mt-2 border-[3px] border-dashed border-ink p-4">Nothing here yet. Open any technology in Rankings and choose "Add to watchlist".</p>
        ) : (
          <ul className="mt-3 flex flex-col gap-3">
            {profile.watchlist.map((w) => (
              <li key={w.slug} className="flex flex-wrap items-center justify-between gap-3 border-[3px] border-ink p-3 shadow-brut-xs">
                <button type="button" onClick={() => onSelect(w.slug)} className="cursor-pointer text-left font-bold underline decoration-2 underline-offset-4 hover:bg-sun">
                  {w.name}
                </button>
                <span className="text-sm">
                  {categoryName(w.category)}, score {w.devintel_score != null ? Math.round(w.devintel_score) : 'n/a'}
                  {growthText(w.growth_30d) ? `, ${growthText(w.growth_30d)} in 30 days` : ''}
                  {w.is_emerging ? ', taking off' : ''}
                </span>
                <button type="button" disabled={busy} className="press cursor-pointer border-2 border-ink bg-white px-3 text-sm font-bold"
                  onClick={() => run(async () => setProfile({ ...profile, watchlist: await removeFromWatchlist(w.slug) }), `${w.name} removed`)}>
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {notice && <p className="border-[3px] border-ink bg-sun p-3 font-bold" role="status">{notice}</p>}

      <section className="border-[3px] border-ink bg-hot p-5">
        <h2 className="font-display text-2xl leading-tight">Delete my account</h2>
        <p className="mb-3 text-sm">This permanently deletes your account, saved skills and watchlist. It cannot be undone.</p>
        <button type="button" disabled={busy} className={`${btn} bg-white`}
          onClick={() => window.confirm('Delete your account and everything saved with it?') &&
            run(async () => { await deleteAccount(); window.location.href = '/' }, '')}>
          Delete my account
        </button>
      </section>
    </div>
  )
}

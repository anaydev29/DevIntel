import { useEffect, useRef, useState } from 'react'
import { analyzeSkills, saveSkills } from '../lib/api'
import { categoryName, growthText } from '../lib/format'
import { useAuth } from '../lib/auth'
import SkillPicker from './SkillPicker'

const SOURCE_LABEL = { manual: 'you picked it', github: 'found on GitHub', both: 'picked and found on GitHub' }

function Sticker({ children, color = 'bg-white' }) {
  return <span className={`border-2 border-ink px-2 text-sm font-bold ${color}`}>{children}</span>
}

export default function SkillGapPage({ technologies }) {
  const [picked, setPicked] = useState(new Set())
  const [username, setUsername] = useState('')
  const [state, setState] = useState({ status: 'idle', data: null, error: '' })

  const { authenticated, profile, setProfile } = useAuth()
  const [saved, setSaved] = useState('')
  const prefilled = useRef(false)

  // Pre-fill from the signed-in user's saved profile, once
  useEffect(() => {
    if (profile && !prefilled.current) {
      prefilled.current = true
      setPicked(new Set(profile.skills))
      setUsername(profile.user.github_username ?? '')
    }
  }, [profile])

  async function saveToProfile() {
    try {
      await saveSkills([...picked])
      setProfile({ ...profile, skills: [...picked] })
      setSaved('Saved to your profile')
    } catch (e) {
      setSaved(e.message)
    }
  }

  const toggle = (slug) => setPicked((prev) => {
    const next = new Set(prev)
    next.has(slug) ? next.delete(slug) : next.add(slug)
    return next
  })

  async function run() {
    setState({ status: 'loading', data: null, error: '' })
    try {
      const data = await analyzeSkills({ skills: [...picked], github_username: username.trim() || null })
      setState({ status: 'done', data, error: '' })
    } catch (e) {
      setState({ status: 'error', data: null, error: e.message })
    }
  }

  const canRun = (picked.size > 0 || username.trim()) && state.status !== 'loading'
  const d = state.data

  return (
    <section className="border-[3px] border-ink bg-white p-5 shadow-brut">
      <h2 className="font-display text-3xl leading-tight">Skill gap analyzer</h2>
      <p className="mb-5 text-[0.95rem]">Tell us what you already know and we will rank what to learn next, using demand, momentum and how well it fits your stack.</p>

      <h3 className="mb-2 font-display text-xl">1. Pick the technologies you know</h3>
      <div className="mb-5"><SkillPicker technologies={technologies} picked={picked} onToggle={toggle} /></div>

      <h3 className="mb-2 font-display text-xl">2. Or add your GitHub username (optional)</h3>
      <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="for example octocat" aria-label="GitHub username"
        className="mb-1 w-full max-w-sm border-[3px] border-ink bg-white px-3 py-2.5 shadow-brut-sm" />
      <p className="mb-5 text-sm">We read only your public repositories (main language and topics). Nothing is stored.</p>

      <button type="button" disabled={!canRun} onClick={run}
        className="press cursor-pointer border-[3px] border-ink bg-sun px-6 py-2 text-lg font-bold shadow-brut-sm disabled:cursor-not-allowed disabled:opacity-50">
        {state.status === 'loading' ? 'Analyzing...' : 'Find my gaps'}
      </button>
      {authenticated ? (
        <button type="button" disabled={picked.size === 0} onClick={saveToProfile}
          className="press ml-3 cursor-pointer border-[3px] border-ink bg-white px-6 py-2 text-lg font-bold shadow-brut-sm disabled:cursor-not-allowed disabled:opacity-50">
          Save skills to my profile
        </button>
      ) : (
        <p className="mt-3 text-sm">Sign in to save your skills and have them filled in next time.</p>
      )}
      {saved && <p className="mt-3 font-bold" role="status">{saved}</p>}

      {state.status === 'error' && <p className="mt-5 border-[3px] border-ink bg-hot p-4 font-bold" role="alert">{state.error}</p>}

      {d && (
        <div className="mt-8">
          <p className="mb-5 border-[3px] border-ink bg-sun p-4 text-lg font-bold shadow-brut-sm">
            You know {d.known.length} tracked {d.known.length === 1 ? 'technology' : 'technologies'}, and {d.coverage.known_in_top10} of the top 10 by DevIntel Score.
            {d.github && ` We scanned ${d.github.repos_scanned} public repositories of @${d.github.username}.`}
          </p>

          {d.known.length > 0 && (
            <div className="mb-6">
              <h3 className="mb-2 font-display text-xl">Your stack</h3>
              <div className="flex flex-wrap gap-2">
                {d.known.map((k) => (
                  <Sticker key={k.slug} color="bg-mint">
                    {k.name}{k.devintel_score != null ? `, score ${Math.round(k.devintel_score)}` : ''} ({SOURCE_LABEL[k.source]}{k.repos ? `, ${k.repos} repos` : ''})
                  </Sticker>
                ))}
              </div>
            </div>
          )}
          {d.unrecognized.length > 0 && <p className="mb-4 text-sm">Not tracked yet: {d.unrecognized.join(', ')}</p>}

          <h3 className="mb-1 font-display text-2xl">Learn next</h3>
          <p className="mb-3 text-sm">Priority mixes demand (55%), momentum (25%) and fit with your stack (20%).</p>
          {d.note && <p className="border-[3px] border-dashed border-ink p-4">{d.note}</p>}
          <ol className="flex flex-col gap-3">
            {d.recommendations.map((r, i) => (
              <li key={r.slug} className="grid grid-cols-[2rem_1fr] gap-3 border-[3px] border-ink bg-white p-4 shadow-brut-sm">
                <span className="font-display text-xl">{i + 1}</span>
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xl font-bold">{r.name}</span>
                    <Sticker color="bg-lilac">{categoryName(r.category)}</Sticker>
                    {r.is_emerging && <Sticker color="bg-hot">Taking off</Sticker>}
                    {r.growth_30d != null && !r.is_emerging && <Sticker>{growthText(r.growth_30d)} in 30 days</Sticker>}
                  </div>
                  <div className="my-2 flex items-center gap-2.5">
                    <span className="h-4 flex-1 border-[3px] border-ink bg-white">
                      <span className="block h-full border-r-[3px] border-ink bg-sky" style={{ width: `${Math.max(2, r.priority)}%` }} />
                    </span>
                    <span className="min-w-9 text-right font-display text-lg">{Math.round(r.priority)}</span>
                  </div>
                  <ul className="mb-2 list-disc pl-5 text-sm">{r.reasons.map((x) => <li key={x}>{x}</li>)}</ul>
                  {r.starters.length > 0 && (
                    <p className="text-sm">
                      <span className="font-bold">Start with: </span>
                      {r.starters.map((a, j) => (
                        <span key={a.url}>
                          {j > 0 && ', '}
                          <a href={a.url} target="_blank" rel="noopener noreferrer" className="underline decoration-2 underline-offset-2 hover:bg-sun">{a.title}</a>
                        </span>
                      ))}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  )
}

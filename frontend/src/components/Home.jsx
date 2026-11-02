import { Component, lazy, Suspense, useEffect, useState } from 'react'
import { Link } from '../lib/router'
import { growthText } from '../lib/format'
import SceneFallback from './SceneFallback'
import WeightCustomizer from './WeightCustomizer'
import {
  DEFAULT_WEIGHTS,
  SIGNALS,
  loadStoredWeights,
  onWeightsChange,
  sharesDiffer,
  storeWeights,
} from '../lib/score'

// three.js is large, so the scene is loaded in the background and the page appears first
const HeroScene = lazy(() => import('./HeroScene'))

class SceneBoundary extends Component {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() { return this.state.failed ? <SceneFallback /> : this.props.children }
}

// These weights are documented at the top of backend/app/analysis.py; keep both in sync.
const WEIGHTS = [
  ['Stack Overflow questions, 30 days', 25, 'bg-sky'],
  ['Hacker News job posts', 20, 'bg-hot'],
  ['GitHub repositories', 15, 'bg-sun'],
  ['Stars on top repositories', 15, 'bg-mint'],
  ['Hacker News stories', 10, 'bg-lilac'],
  ['Stack Overflow, all time', 10, 'bg-white'],
  ['Hacker News points', 5, 'bg-ink'],
]

const TILES = [
  ['/rankings', '01', 'Rankings', 'Every technology scored from 0 to 100, with 30-day growth, filters and sorting.', 'bg-sun', 'Open rankings'],
  ['/compare', '02', 'Compare', 'Put two technologies head to head and see which one leads on each signal.', 'bg-sky', 'Start a duel'],
  ['/skills', '03', 'Skill gap', 'Enter your skills or a GitHub username and get ranked advice on what to learn next.', 'bg-mint', 'Find my next skill'],
  ['/topics', '04', 'Topics', 'Ask questions, share advice, and start discussions about any technology.', 'bg-lime', 'Join discussion'],
  ['/news', '05', 'News', 'The Hacker News front page, collected every day.', 'bg-white', 'Read the news'],
  ['/blogs', '06', 'Blogs', 'Popular Dev.to articles from the last two weeks, filterable by technology.', 'bg-lilac', 'Browse articles'],
  ['/repos', '07', 'Trending repos', 'The most-starred GitHub repositories created in the last 7 days.', 'bg-hot', 'See what is new'],
]

function Stat({ label, value, note }) {
  return (
    <div className="di-stat">
      <div className="di-stat__label">{label}</div>
      <div className="di-stat__value">{value}</div>
      {note && <div className="di-stat__note">{note}</div>}
    </div>
  )
}

function MiniRow({ rank, tech, onSelect }) {
  const growth = growthText(tech.growth_30d)
  return (
    <li>
      <button type="button" className="di-row di-row--mini" onClick={() => onSelect(tech.slug)}>
        <span className={`di-rank di-rank--${rank <= 3 ? rank : 'x'}`}>{rank}</span>
        <span className="di-row__name">{tech.name}</span>
        <span className="di-bar__num">{Math.round(tech.devintel_score ?? 0)}<small style={{ fontFamily: 'var(--di-body)', fontSize: '0.75rem' }}> / 100</small></span>
        <span className={`di-growth ${growth == null ? 'di-growth--na' : tech.growth_30d > 0 ? 'di-growth--up' : ''}`}>{growth ?? 'n/a'}</span>
      </button>
    </li>
  )
}

export default function Home({ data, onSelect }) {
  const [customizing, setCustomizing] = useState(false)
  const [weights, setWeights] = useState(() => loadStoredWeights() ?? { ...DEFAULT_WEIGHTS })

  useEffect(() => {
    return onWeightsChange((next) => {
      setWeights(next ? { ...next } : { ...DEFAULT_WEIGHTS })
    })
  }, [])

  const isCustom = sharesDiffer(weights, DEFAULT_WEIGHTS)
  const metricKeys = Object.keys(SIGNALS)
  const totalWeight = metricKeys.reduce((sum, m) => sum + (weights[m] ?? 0), 0)
  const shares = Object.fromEntries(
    metricKeys.map((m) => [m, totalWeight > 0 ? Math.round((100 * (weights[m] ?? 0)) / totalWeight) : 0]),
  )

  const items = data ? [...data.items].sort((a, b) => (b.devintel_score ?? 0) - (a.devintel_score ?? 0)) : []
  const emerging = data?.emerging ?? []
  const top = items.slice(0, 5)
  const tickerItems = items.slice(0, 14)

  return (
    <>
      <section className="di-wrap di-hero" aria-labelledby="di-hero-title">
        <div>
          <span className="di-kicker">Developer intelligence</span>
          <h1 id="di-hero-title" className="di-h1">
            Stop guessing{' '}
            <span className="di-mark di-mark--sun">what to learn.</span>{' '}
            Decode tech momentum{' '}
            <span className="di-mark di-mark--white">in real time.</span>
          </h1>
          <p className="di-lead">
            DevIntel reads GitHub, Stack Overflow, Hacker News and Dev.to every day and turns them into one transparent 0 to 100 score, plus a 30-day growth signal that shows what is rising.
          </p>
          <div className="di-cta-row">
            <Link to="/rankings" className="di-btn di-btn--lime">See the rankings &rarr;</Link>
            <Link to="/skills" className="di-btn">Find my next skill</Link>
          </div>
          <div className="di-stats">
            <Stat label="Technologies tracked" value={data ? items.length : '...'} note="across 7 daily collectors" />
            <Stat label="Taking off now" value={data ? emerging.length : '...'} note={emerging.length === 0 && data ? 'needs a few days of history' : 'flagged by 4 strict checks'} />
            <Stat label="Top ranked" value={top[0]?.name ?? '...'} note={top[0] ? `score ${Math.round(top[0].devintel_score ?? 0)} of 100` : undefined} />
          </div>
        </div>

        <div className="di-scene">
          <div className="di-scene__stage">
            <SceneBoundary>
              <Suspense fallback={<SceneFallback message="Loading the 3D view..." />}>
                <HeroScene />
              </Suspense>
            </SceneBoundary>
            {top.length > 0 && (
              <div className="di-scene__chips">
                {top.slice(0, 3).map((t, i) => (
                  <span key={t.slug} className={`di-chip ${['bg-sun', 'bg-mint', 'bg-lilac'][i]}`}>#{i + 1} {t.name} {Math.round(t.devintel_score ?? 0)}</span>
                ))}
              </div>
            )}
          </div>
          <p className="di-scene__caption"><span className="di-sticker bg-lime">Drag to rotate. Click to spin.</span></p>
        </div>
      </section>

      {tickerItems.length > 0 && (
        <div className="di-ticker" aria-hidden="true">
          <div className="di-ticker__track">
            {[...tickerItems, ...tickerItems].map((t, i) => (
              <span key={`${t.slug}-${i}`} className="di-ticker__item">
                {t.name} <b>{Math.round(t.devintel_score ?? 0)}</b>
                {t.growth_30d != null && <i>{growthText(t.growth_30d)}</i>}
              </span>
            ))}
          </div>
        </div>
      )}

      <section className="di-wrap di-section" aria-labelledby="di-board-title">
        <div className="di-section__head">
          <h2 id="di-board-title" className="di-h2">Live leaderboard</h2>
          <p className="di-sub">The five highest scores right now. Select a technology to see every number behind its score.</p>
        </div>
        <div className="di-split">
          <div className="di-panel">
            <ol className="di-list">
              {top.length === 0 ? (
                <li className="di-empty">{data ? 'No scores yet. Run python run_pipeline.py in the backend folder to collect data.' : 'Loading the leaderboard...'}</li>
              ) : (
                top.map((t, i) => <MiniRow key={t.slug} rank={i + 1} tech={t} onSelect={onSelect} />)
              )}
            </ol>
            <p style={{ margin: '18px 0 0' }}><Link to="/rankings" className="di-btn di-btn--sm di-btn--ink">All {items.length || ''} technologies &rarr;</Link></p>
          </div>
          <aside className="di-panel di-panel--hot" aria-labelledby="di-take-title">
            <h2 id="di-take-title">Taking off</h2>
            <p className="di-panel__hint">Growing much faster than the rest over the last 30 days.</p>
            <ul className="di-list">
              {emerging.length === 0 ? (
                <li className="di-empty">Nothing flagged yet. Growth needs a few days of collected data, and a new day is added every morning.</li>
              ) : (
                emerging.slice(0, 4).map((t) => (
                  <li key={t.slug}>
                    <button type="button" className="di-row di-row--duo" onClick={() => onSelect(t.slug)}>
                      <span className="di-row__name">{t.name}</span>
                      <span className="di-growth di-growth--up">{growthText(t.growth_30d)}</span>
                    </button>
                  </li>
                ))
              )}
            </ul>
          </aside>
        </div>
      </section>

      <section className="di-wrap di-section" aria-labelledby="di-weights-title">
        <div className="di-section__head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 14 }}>
          <div>
            <h2 id="di-weights-title" className="di-h2">Transparent scoring</h2>
            <p className="di-sub">Eight signals from four independent developer platforms. No black boxes.</p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            {isCustom && (
              <span className="di-chip bg-hot" style={{ fontWeight: 700 }}>⚡ Custom weights active</span>
            )}
            <button
              type="button"
              className={`di-btn di-btn--sm ${isCustom ? 'di-btn--lime' : ''}`}
              onClick={() => setCustomizing((c) => !c)}
              aria-expanded={customizing}
            >
              {customizing ? 'Close weight sliders' : isCustom ? 'Edit custom weights' : 'Customize signal weights'}
            </button>
            {isCustom && (
              <button
                type="button"
                className="di-btn di-btn--sm"
                onClick={() => storeWeights(null)}
              >
                Reset
              </button>
            )}
          </div>
        </div>

        {/* Dynamic score weights bar */}
        <div
          className="di-wbar"
          role="img"
          aria-label={`Score weights: ${metricKeys.map((m) => `${SIGNALS[m].name} ${shares[m]} percent`).join(', ')}`}
        >
          {metricKeys.map((m) => {
            const pct = shares[m]
            if (pct <= 0) return null
            const sig = SIGNALS[m]
            return (
              <div
                key={m}
                className={`di-wseg ${sig.color}`}
                style={{ flexBasis: `${pct}%`, flexGrow: pct }}
                title={`${sig.name}: ${pct}%`}
              >
                {pct >= 6 ? `${pct}%` : ''}
              </div>
            )
          })}
        </div>

        {customizing ? (
          <WeightCustomizer
            showBar={false}
            onClose={() => setCustomizing(false)}
            extraAction={
              <Link to="/rankings" className="di-btn di-btn--sm di-btn--lime">
                View rankings with your weights &rarr;
              </Link>
            }
          />
        ) : (
          <>
            <ul className="di-legend">
              {metricKeys.map((m) => {
                const pct = shares[m]
                const sig = SIGNALS[m]
                return (
                  <li key={m} style={{ opacity: pct === 0 ? 0.45 : 1 }}>
                    <span className={`di-swatch ${sig.color}`} />
                    <span>{sig.name}</span>
                    <b style={{ marginLeft: 4, fontFamily: 'var(--di-display)' }}>({pct}%)</b>
                  </li>
                )
              })}
            </ul>
            <div style={{ marginTop: 16, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              <button
                type="button"
                className="di-btn di-btn--sm"
                onClick={() => setCustomizing(true)}
              >
                Customize weights with sliders &rarr;
              </button>
              {isCustom && (
                <Link to="/rankings" className="di-btn di-btn--sm di-btn--lime">
                  See rankings with your weights &rarr;
                </Link>
              )}
            </div>
          </>
        )}
      </section>

      <section className="di-wrap di-section" aria-labelledby="di-explore-title">
        <div className="di-section__head">
          <h2 id="di-explore-title" className="di-h2">Explore DevIntel</h2>
          <p className="di-sub">Seven views, one dataset.</p>
        </div>
        <div className="di-tiles">
          {TILES.map(([to, no, title, text, color, go]) => (
            <Link key={to} to={to} className={`di-tile di-lift ${color}`}>
              <span className="di-tile__top"><span className="di-tile__no">{no}</span><span aria-hidden="true">&rarr;</span></span>
              <h3>{title}</h3>
              <p>{text}</p>
              <span className="di-tile__go">{go}</span>
            </Link>
          ))}
        </div>
      </section>

      <section className="di-band" aria-labelledby="di-band-title">
        <div className="di-wrap">
          <h2 id="di-band-title" className="di-h2">Cut through the opinions. See the data.</h2>
          <div className="di-cta-row">
            <Link to="/rankings" className="di-btn di-btn--ink">Launch the dashboard &rarr;</Link>
            <a href="https://github.com/anaydev29/DevIntel" target="_blank" rel="noopener noreferrer" className="di-btn">View the code on GitHub</a>
          </div>
        </div>
      </section>
    </>
  )
}

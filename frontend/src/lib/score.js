// Same formula as the backend: the weighted average of the ranks a technology earned on the signals it has,
// scaled to 0-100. Signals a technology has no data for are left out and the other weights are re-balanced.
export function scoreFor(components, weights) {
  let sum = 0
  let total = 0
  for (const [metric, c] of Object.entries(components)) {
    const w = weights[metric] ?? 0
    sum += w * c.rank
    total += w
  }
  return total > 0 ? (100 * sum) / total : null
}

export const SIGNALS = {
  'stackoverflow.questions_30d': {
    name: 'Stack Overflow questions, 30 days',
    short: 'SO questions (30d)',
    platform: 'Stack Overflow',
    color: 'bg-sky',
    defaultWeight: 22,
  },
  'hiring.share_pct': {
    name: 'Hacker News job posts',
    short: 'HN job posts',
    platform: 'Hacker News',
    color: 'bg-hot',
    defaultWeight: 18,
  },
  'github.repo_count': {
    name: 'GitHub repositories',
    short: 'GitHub repos',
    platform: 'GitHub',
    color: 'bg-sun',
    defaultWeight: 13,
  },
  'github.top_stars': {
    name: 'Stars on top repositories',
    short: 'Top repo stars',
    platform: 'GitHub',
    color: 'bg-mint',
    defaultWeight: 13,
  },
  'wikipedia.views_30d': {
    name: 'Wikipedia page views',
    short: 'Wikipedia views',
    platform: 'Wikipedia',
    color: 'bg-lime',
    defaultWeight: 12,
  },
  'hackernews.stories_30d': {
    name: 'Hacker News stories',
    short: 'HN stories',
    platform: 'Hacker News',
    color: 'bg-lilac',
    defaultWeight: 9,
  },
  'stackoverflow.total_questions': {
    name: 'Stack Overflow, all time',
    short: 'SO all time',
    platform: 'Stack Overflow',
    color: 'bg-white',
    defaultWeight: 8,
  },
  'hackernews.points_30d': {
    name: 'Hacker News points',
    short: 'HN points',
    platform: 'Hacker News',
    color: 'bg-ink',
    defaultWeight: 5,
  },
}

export const DEFAULT_WEIGHTS = Object.fromEntries(
  Object.entries(SIGNALS).map(([k, s]) => [k, s.defaultWeight]),
)

export const SIGNAL_PRESETS = [
  {
    name: 'Default',
    desc: 'DevIntel balanced baseline',
    weights: { ...DEFAULT_WEIGHTS },
  },
  {
    name: 'GitHub heavy',
    desc: 'Emphasize repos & code stars',
    weights: {
      'github.repo_count': 35,
      'github.top_stars': 35,
      'stackoverflow.questions_30d': 10,
      'wikipedia.views_30d': 10,
      'hiring.share_pct': 5,
      'hackernews.stories_30d': 5,
      'stackoverflow.total_questions': 0,
      'hackernews.points_30d': 0,
    },
  },
  {
    name: 'Hiring & Jobs',
    desc: 'Focus on hiring market demand',
    weights: {
      'hiring.share_pct': 45,
      'stackoverflow.questions_30d': 25,
      'github.repo_count': 15,
      'stackoverflow.total_questions': 15,
      'github.top_stars': 0,
      'wikipedia.views_30d': 0,
      'hackernews.stories_30d': 0,
      'hackernews.points_30d': 0,
    },
  },
  {
    name: 'Community Buzz',
    desc: 'Focus on Hacker News discussions',
    weights: {
      'hackernews.stories_30d': 35,
      'hackernews.points_30d': 25,
      'stackoverflow.questions_30d': 20,
      'hiring.share_pct': 10,
      'wikipedia.views_30d': 10,
      'github.repo_count': 0,
      'github.top_stars': 0,
      'stackoverflow.total_questions': 0,
    },
  },
  {
    name: 'Equal signals',
    desc: 'All 8 signals count equally',
    weights: Object.fromEntries(Object.keys(SIGNALS).map((k) => [k, 12])),
  },
]

const STORAGE_KEY = 'devintel.score-weights'

export function loadStoredWeights() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) ?? null
  } catch {
    return null
  }
}

export function storeWeights(weights) {
  try {
    if (weights) localStorage.setItem(STORAGE_KEY, JSON.stringify(weights))
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* private mode or full storage: the sliders still work, they just are not remembered */
  }
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('devintel:weights-changed', { detail: weights }))
  }
}

export function onWeightsChange(callback) {
  if (typeof window === 'undefined') return () => {}
  const handler = () => callback(loadStoredWeights())
  window.addEventListener('devintel:weights-changed', handler)
  window.addEventListener('storage', handler)
  return () => {
    window.removeEventListener('devintel:weights-changed', handler)
    window.removeEventListener('storage', handler)
  }
}

export function defaultWeights(weights) {
  if (!weights) return DEFAULT_WEIGHTS
  return Object.fromEntries(Object.entries(weights).map(([m, w]) => [m, Math.round(w * 100)]))
}

export function sharesDiffer(a, b) {
  if (!a || !b) return false
  const total = (o) => Object.values(o).reduce((x, y) => x + y, 0) || 1
  return Object.keys(a).some((m) => Math.abs(a[m] / total(a) - (b[m] ?? 0) / total(b)) > 0.005)
}

export const compact = new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 })

export const METRIC_LABELS = {
  'github.repo_count': 'GitHub repositories tagged',
  'github.top_stars': 'Stars on the top 10 repositories',
  'github.top_forks': 'Forks on the top 10 repositories',
  'stackoverflow.total_questions': 'Stack Overflow questions, all time',
  'stackoverflow.questions_30d': 'Stack Overflow questions, last 30 days',
  'hackernews.stories_30d': 'Hacker News stories, last 30 days',
  'hackernews.points_30d': 'Hacker News points, last 30 days',
  'hiring.mentions': 'Job posts mentioning it (latest HN hiring thread)',
  'hiring.share_pct': 'Share of HN job posts mentioning it',
  'npm.downloads_week': 'npm downloads, last week',
  'pypi.downloads_week': 'PyPI downloads, last week',
}

// Percent metrics end in _pct; everything else is a count
export const formatMetric = (key, value) =>
  key.endsWith('_pct') ? `${value.toFixed(1)}%` : compact.format(value)

const CATEGORY_NAMES = { 'ai-ml': 'AI and ML', devops: 'DevOps' }
export const categoryName = (c) => CATEGORY_NAMES[c] ?? c.charAt(0).toUpperCase() + c.slice(1)

export function growthText(g) {
  if (g == null) return null
  const pct = Math.round(g * 100)
  return `${pct >= 0 ? '+' : ''}${pct}%`
}

export function timeAgo(iso) {
  // The API returns UTC without a timezone suffix, so add one before parsing
  const hasZone = /[zZ]|[+-]\d\d:?\d\d$/.test(iso)
  const minutes = Math.max(0, Math.round((Date.now() - new Date(hasZone ? iso : `${iso}Z`)) / 60000))
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes} min ago`
  if (minutes < 1440) return `${Math.round(minutes / 60)} h ago`
  const days = Math.round(minutes / 1440)
  return `${days} ${days === 1 ? 'day' : 'days'} ago`
}

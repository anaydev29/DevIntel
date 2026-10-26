// Public data only changes when the daily pipeline runs, so reuse answers for a minute. This also merges
// identical requests that are already in flight. Anything personal (profile, discussions...) is never cached.
const PUBLIC = ['/rankings', '/technologies', '/categories', '/pipeline', '/feed', '/compare']
const CACHE_MS = 60_000
const cache = new Map()

async function get(path) {
  const cacheable = PUBLIC.some((p) => path.startsWith(p))
  if (cacheable) {
    const hit = cache.get(path)
    if (hit && hit.expires > Date.now()) return hit.promise
  }
  const promise = fetch(path).then((res) => {
    if (!res.ok) throw new Error(`${path} returned ${res.status}`)
    return res.json()
  })
  if (cacheable) {
    cache.set(path, { promise, expires: Date.now() + CACHE_MS })
    promise.catch(() => cache.delete(path))
  }
  return promise
}

export async function loadDashboard() {
  const [items, emerging, categories, runs] = await Promise.all([
    get('/rankings/trending?limit=100'),
    get('/rankings/emerging?limit=10'),
    get('/categories'),
    get('/pipeline/runs?limit=20'),
  ])
  return { items, emerging, categories, runs }
}

export const loadTechnology = (slug) => get(`/technologies/${encodeURIComponent(slug)}`)

export const loadBlogs = (tech) => get(`/feed/blogs?limit=40${tech ? `&tech=${encodeURIComponent(tech)}` : ''}`)
export const loadNews = () => get('/feed/news?limit=30')
export const loadRepos = () => get('/feed/repos?limit=100')

export const loadCompare = (a, b) => get(`/compare?techs=${encodeURIComponent(a)},${encodeURIComponent(b)}`)

export async function analyzeSkills(payload) {
  const res = await fetch('/skills/gap', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const data = await res.json().catch(() => null)
  if (!res.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : 'Something went wrong. Please try again.')
  return data
}

async function send(method, path, body) {
  const res = await fetch(path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (res.status === 204) return null
  const data = await res.json().catch(() => null)
  if (!res.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : 'Something went wrong. Please try again.')
  return data
}

export const authMe = () => get('/auth/me')
export const signOutRequest = () => send('POST', '/auth/logout')
export const loadProfile = () => get('/me/profile')
export const saveGithubUsername = (username) => send('PUT', '/me/profile', { github_username: username })
export const saveSkills = (skills) => send('PUT', '/me/skills', { skills })
export const addToWatchlist = (slug) => send('PUT', `/me/watchlist/${encodeURIComponent(slug)}`)
export const removeFromWatchlist = (slug) => send('DELETE', `/me/watchlist/${encodeURIComponent(slug)}`)
export const deleteAccount = () => send('DELETE', '/me')

export const loadDiscussion = (kind, ref) => get(`/discussions?kind=${kind}&ref=${encodeURIComponent(ref)}`)
export const loadCounts = (kind, refs) => get(`/discussions/counts?kind=${kind}&refs=${encodeURIComponent(refs.join(','))}`)
export const postComment = (kind, ref, body, parentId) => send('POST', '/discussions/comments', { kind, ref, body, parent_id: parentId ?? null })
export const editComment = (id, body) => send('PUT', `/discussions/comments/${id}`, { body })
export const deleteComment = (id) => send('DELETE', `/discussions/comments/${id}`)
export const voteComment = (id, voted) => send('PUT', `/discussions/comments/${id}/vote`, { voted })
export const reportComment = (id, reason) => send('POST', `/discussions/comments/${id}/report`, { reason })

export const modQueue = () => get('/moderation/queue')
export const modLog = () => get('/moderation/log?limit=30')
export const modAction = (id, action, note) => send('POST', `/moderation/comments/${id}/action`, { action, note })
export const modBan = (userId, reason) => send('POST', `/moderation/users/${userId}/ban`, { reason })
export const modUnban = (userId) => send('DELETE', `/moderation/users/${userId}/ban`)
export const adminUsers = () => get('/moderation/users')
export const adminSetRole = (userId, role) => send('PUT', `/moderation/users/${userId}/role`, { role })

export const loadBreakdown = () => get('/rankings/breakdown')

export const loadTechPage = (slug) => get(`/technologies/${encodeURIComponent(slug)}/page`)
export const loadTopics = (tech, sort = 'active', limit = 30) =>
  get(`/topics?sort=${sort}&limit=${limit}${tech ? `&tech=${encodeURIComponent(tech)}` : ''}`)
export const loadTopic = (ref) => get(`/topics/${encodeURIComponent(ref)}`)
export const createTopic = (payload) => send('POST', '/topics', payload)

export const loadHistory = (slug, days = 90) => get(`/technologies/${encodeURIComponent(slug)}/history?days=${days}`)
export const loadBacktest = (horizon = 14) => get(`/rankings/backtest?horizon=${horizon}`)

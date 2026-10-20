async function get(path) {
  const res = await fetch(path)
  if (!res.ok) throw new Error(`${path} returned ${res.status}`)
  return res.json()
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

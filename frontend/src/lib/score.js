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
}

export function defaultWeights(weights) {
  return Object.fromEntries(Object.entries(weights).map(([m, w]) => [m, Math.round(w * 100)]))
}

export function sharesDiffer(a, b) {
  const total = (o) => Object.values(o).reduce((x, y) => x + y, 0) || 1
  return Object.keys(a).some((m) => Math.abs(a[m] / total(a) - (b[m] ?? 0) / total(b)) > 0.005)
}

import { loadCounts } from './api'
import { useAsync } from './useAsync'

// Comment counts for a list of items, e.g. useCounts('article', ids) -> { "12": 3 }. Fails quietly.
export function useCounts(kind, refs) {
  const key = refs.join(',')
  const state = useAsync(() => (key ? loadCounts(kind, refs).catch(() => ({})) : Promise.resolve({})), [kind, key])
  return state.data ?? {}
}

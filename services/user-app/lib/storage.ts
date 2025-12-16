import { HistoryItem, QueryMode, QueryResponse } from './types'

const HISTORY_KEY = 'continuuai_history'
const MAX_HISTORY_ITEMS = 50

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

export function getHistory(): HistoryItem[] {
  if (typeof window === 'undefined') return []
  
  try {
    const data = localStorage.getItem(HISTORY_KEY)
    if (!data) return []
    return JSON.parse(data) as HistoryItem[]
  } catch {
    return []
  }
}

export function saveQuery(
  query: string,
  mode: QueryMode,
  response: QueryResponse
): HistoryItem {
  const item: HistoryItem = {
    id: generateId(),
    query,
    mode,
    response,
    timestamp: Date.now()
  }

  const history = getHistory()
  const updated = [item, ...history].slice(0, MAX_HISTORY_ITEMS)
  
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(updated))
  } catch {
    // Storage full or unavailable - silently fail
  }

  return item
}

export function deleteHistoryItem(id: string): void {
  const history = getHistory()
  const updated = history.filter(item => item.id !== id)
  
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(updated))
  } catch {
    // Silently fail
  }
}

export function clearHistory(): void {
  try {
    localStorage.removeItem(HISTORY_KEY)
  } catch {
    // Silently fail
  }
}

export function getHistoryItem(id: string): HistoryItem | null {
  const history = getHistory()
  return history.find(item => item.id === id) || null
}

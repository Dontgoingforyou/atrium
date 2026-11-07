export type SearchEntityType =
  | 'document'
  | 'chat_message'
  | 'task'
  | 'specialist'
  | 'learning_material'
  | 'specialist_note'
  | 'calendar_event'
  | 'agreement'

/** Режим на странице /search: подстрока в БД или векторы в portal_embedding. */
export type PortalSearchMode = 'fulltext' | 'semantic'

export type SearchResult = {
  entity_type: SearchEntityType
  entity_id: string
  title: string | null
  snippet: string | null
  created_at: string | null
  nav_node_slug: string | null
  /** Только семантический поиск: косинусная похожесть 0–1 */
  similarity_score?: number | null
  /** Для chat_message — вложенный объект чата */
  chat?: { id: string; title: string | null } | null
  /** Для chat_message — вложенный объект сообщения */
  message?: { id: string; body: string } | null
  /** Для specialist_note — sub специалиста из meta */
  specialist_sub?: string | null
}

export type SearchParams = {
  q: string
  types?: SearchEntityType[]
  tag_slugs?: string[]
  status_ids?: string[]
  skip?: number
  limit?: number
}

export type SemanticSearchParams = SearchParams

export type SemanticSearchResponse = {
  query: string
  results: SearchResult[]
  total_found: number
}

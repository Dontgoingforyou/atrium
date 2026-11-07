export type PortalDocument = {
  id: string
  title: string
  icon_emoji?: string | null
  body: string | null
  nav_node_slug: string | null
  parent_document_id: string | null
  breadcrumb: { id: string; title: string }[]
  author_sub: string
  owner_sub: string | null
  version: number
  created_at: string
  updated_at: string
  tags: PortalTag[]
}

export type PortalDocumentBrief = {
  id: string
  title: string
  icon_emoji?: string | null
  parent_document_id: string | null
  author_sub: string
  version?: number
  created_at: string
  updated_at: string
}

export type PortalDocumentHistory = {
  id: string
  document_id: string
  changed_at: string
  changed_by_sub: string
  diff: Record<string, { old: unknown; new: unknown }>
}

export type PortalTag = {
  id: string
  name: string
  slug: string
  color: string
  version: number
}

export type PortalDocumentTrashItem = {
  id: string
  title: string
  deleted_at: string
  deleted_by_sub: string | null
  deleted_by_display_name: string | null
  deleted_by_email: string | null
  auto_purge_at: string
}

export type PortalDocumentCreate = {
  title: string
  icon_emoji?: string | null
  parent_document_id?: string | null
  body?: string | null
  owner_sub?: string | null
  tag_ids?: string[]
}

export type PortalDocumentUpdate = {
  expected_version: number
  title?: string
  icon_emoji?: string | null
  parent_document_id?: string | null
  body?: string | null
  owner_sub?: string | null
  tag_ids?: string[] | null
}

export type PortalDocumentQuickCreate = {
  parent_document_id?: string | null
}

export type PortalDocumentReorderRequest = {
  before_id?: string | null
  after_id?: string | null
}

export type DocumentFile = {
  id: string
  document_id: string
  original_filename: string
  content_type: string
  file_size: number
  download_url: string
  view_url: string
  uploaded_by_sub: string
  created_at: string
}

export type PortalTagCreate = {
  name: string
  color?: string
}

export type PortalTagUpdate = {
  expected_version: number
  name?: string
  color?: string
}

export type NavDocBrief = {
  id: string
  title: string
  icon_emoji?: string | null
  children?: NavDocBrief[]
  shortcuts?: NavDocBrief[]
}

export type PortalNavNodeTree = {
  id: string
  slug: string
  title: string
  sort_order: number
  document_count_subtree: number
  documents?: NavDocBrief[]
  children: PortalNavNodeTree[]
}

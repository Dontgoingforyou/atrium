export type FavoriteTargetType = 'document'

export type PortalFavorite = {
  id: string
  target_type: FavoriteTargetType
  target_id: string
  created_at: string
  title: string
}

export type FavoriteCreate = {
  target_type: 'document'
  target_id: string
}

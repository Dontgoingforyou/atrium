/** Изображение rich-text (согласовано с `RichMediaRead` бэкенда). */
export type RichMediaRead = {
  id: string
  content_type: string
  file_size: number
  original_filename: string
  /** Путь API без хоста, например /api/v1/portal/rich-media/{id}/file. */
  file_path: string
  /** Временный presigned URL для отображения. */
  download_url: string
  created_at: string
}

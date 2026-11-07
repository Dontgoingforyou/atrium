export function selectStableImageUrl(
  imageUrl: string | null | undefined,
  displayedUrl: string | null | undefined,
  holdWhenEmpty: boolean,
): string | null | undefined {
  if (imageUrl) return displayedUrl
  return holdWhenEmpty ? displayedUrl : imageUrl
}

import { parseRepeatedSearchParam, setRepeatedSearchParam } from '../../utils/searchParamsUtils'

export function parseTagSlugsFromSearchParams(params: URLSearchParams): string[] {
  return parseRepeatedSearchParam(params, 'tag_slug')
}

export function setTagSlugsInSearchParams(
  params: URLSearchParams,
  tagSlugs: string[],
): URLSearchParams {
  return setRepeatedSearchParam(params, 'tag_slug', tagSlugs)
}

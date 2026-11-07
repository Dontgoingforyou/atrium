const DEFAULT_JIRA_BASE = 'https://jira.example.com'

export function jiraBrowseUrl(issueKey: string): string {
  const base = (import.meta.env.VITE_JIRA_BASE_URL as string | undefined)?.replace(/\/$/, '') || DEFAULT_JIRA_BASE
  return `${base}/browse/${encodeURIComponent(issueKey)}`
}

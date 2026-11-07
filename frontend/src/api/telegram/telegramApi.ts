import { parseJsonOrThrowApi } from '../parseResponse'
import { authenticatedFetch } from '../rawClient'

export interface TelegramBindInit {
  code: string
  bot_url: string
}

export interface TelegramBindStatus {
  bound: boolean
  created_at: string | null
}

export async function postTelegramBindInit(): Promise<TelegramBindInit> {
  const res = await authenticatedFetch('/telegram/bind/init', { method: 'POST' })
  return parseJsonOrThrowApi(res)
}

export async function getTelegramBindStatus(): Promise<TelegramBindStatus> {
  const res = await authenticatedFetch('/telegram/bind/status')
  return parseJsonOrThrowApi(res)
}

export async function deleteTelegramBind(): Promise<void> {
  const res = await authenticatedFetch('/telegram/bind', { method: 'DELETE' })
  await parseJsonOrThrowApi<void>(res)
}

import type {
  Chat,
  ChatAttachment,
  ChatCreate,
  ChatMessage,
  ChatMessageCreate,
  ChatMessageUpdate,
  MessageReaderItem,
  MessageReactorItem,
} from '../../types/chat'
import type { PortalUser } from '../../types/user'
import type { PagedResponse } from '../../types/timeEntry'
import { parseJsonOrThrowApi } from '../parseResponse'
import { authenticatedFetch, authenticatedUploadWithProgress } from '../rawClient'
import { listPortalUsers as listPortalUsersFromUsersApi } from '../usersApi'

export async function listPortalUsers(params?: { limit?: number }): Promise<PortalUser[]> {
  return listPortalUsersFromUsersApi(params)
}

export async function listChats(params?: {
  skip?: number
  limit?: number
}): Promise<Chat[]> {
  const qs = new URLSearchParams()
  if (params?.skip !== undefined) qs.set('skip', String(params.skip))
  if (params?.limit !== undefined) qs.set('limit', String(params.limit))
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`/portal/chats${query}`)
  return parseJsonOrThrowApi(res)
}

export async function createChat(body: ChatCreate): Promise<Chat> {
  const res = await authenticatedFetch('/portal/chats', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function listMessages(
  chatId: string,
  params?: { skip?: number; limit?: number; aroundMessageId?: string },
): Promise<ChatMessage[]> {
  const qs = new URLSearchParams()
  if (params?.skip !== undefined) qs.set('skip', String(params.skip))
  if (params?.limit !== undefined) qs.set('limit', String(params.limit))
  if (params?.aroundMessageId) qs.set('around_message_id', params.aroundMessageId)
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`/portal/chats/${chatId}/messages${query}`)
  return parseJsonOrThrowApi(res)
}

export async function postMessage(chatId: string, body: ChatMessageCreate): Promise<ChatMessage> {
  const res = await authenticatedFetch(`/portal/chats/${chatId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function patchMessage(
  chatId: string,
  messageId: string,
  body: ChatMessageUpdate,
): Promise<ChatMessage> {
  const res = await authenticatedFetch(`/portal/chats/${chatId}/messages/${messageId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function deleteMessage(
  chatId: string,
  messageId: string,
  scope: 'me' | 'all',
): Promise<void> {
  const qs = new URLSearchParams({ scope })
  const res = await authenticatedFetch(
    `/portal/chats/${chatId}/messages/${messageId}?${qs.toString()}`,
    { method: 'DELETE' },
  )
  await parseJsonOrThrowApi(res)
}

export async function toggleMessageReaction(
  chatId: string,
  messageId: string,
  emoji: string,
): Promise<ChatMessage> {
  const res = await authenticatedFetch(`/portal/chats/${chatId}/messages/${messageId}/reactions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ emoji }),
  })
  return parseJsonOrThrowApi(res)
}

export async function forwardMessage(
  targetChatId: string,
  fromChatId: string,
  messageId: string,
): Promise<ChatMessage> {
  const res = await authenticatedFetch(`/portal/chats/${targetChatId}/messages/forward`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ from_chat_id: fromChatId, message_id: messageId }),
  })
  return parseJsonOrThrowApi(res)
}

export async function getOrCreateDirectChat(otherUserSub: string): Promise<Chat> {
  const res = await authenticatedFetch('/portal/chats/direct', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ other_user_sub: otherUserSub }),
  })
  return parseJsonOrThrowApi(res)
}

export async function patchChatTitle(
  chatId: string,
  title: string,
  expectedVersion: number,
): Promise<Chat> {
  const res = await authenticatedFetch(`/portal/chats/${chatId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, expected_version: expectedVersion }),
  })
  return parseJsonOrThrowApi(res)
}

export async function inviteChatMember(chatId: string, userSub: string): Promise<void> {
  const res = await authenticatedFetch(`/portal/chats/${chatId}/members`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_sub: userSub }),
  })
  await parseJsonOrThrowApi(res)
}

export async function removeChatMember(chatId: string, userSub: string): Promise<void> {
  const enc = encodeURIComponent(userSub)
  const res = await authenticatedFetch(`/portal/chats/${chatId}/members/${enc}`, {
    method: 'DELETE',
  })
  await parseJsonOrThrowApi(res)
}

export async function markChatRead(chatId: string): Promise<void> {
  const res = await authenticatedFetch(`/portal/chats/${chatId}/read`, { method: 'POST' })
  await parseJsonOrThrowApi<void>(res)
}

export async function postGroupChatAvatar(
  chatId: string,
  file: File,
  focal?: { x: number; y: number },
): Promise<{ avatar_url: string; avatar_focal_x?: number | null; avatar_focal_y?: number | null }> {
  const body = new FormData()
  body.append('file', file)
  if (focal !== undefined) {
    body.append('avatar_focal_x', String(focal.x))
    body.append('avatar_focal_y', String(focal.y))
  }
  const res = await authenticatedFetch(`/portal/chats/${chatId}/avatar`, {
    method: 'POST',
    body,
  })
  return parseJsonOrThrowApi(res)
}

export async function deleteGroupChatAvatar(chatId: string): Promise<void> {
  const res = await authenticatedFetch(`/portal/chats/${chatId}/avatar`, { method: 'DELETE' })
  await parseJsonOrThrowApi<void>(res)
}

export async function deleteChatEntirely(chatId: string): Promise<void> {
  const res = await authenticatedFetch(`/portal/chats/${chatId}`, { method: 'DELETE' })
  await parseJsonOrThrowApi<void>(res)
}

export async function uploadAttachment(
  chatId: string,
  file: File,
  voiceMeta?: { durationSeconds: number; waveform: number[] },
  onProgress?: (fraction: number) => void,
): Promise<ChatAttachment> {
  const form = new FormData()
  form.append('file', file)
  if (voiceMeta) {
    form.append('voice_duration_seconds', String(voiceMeta.durationSeconds))
    form.append('voice_waveform', JSON.stringify(voiceMeta.waveform))
  }
  const res = await authenticatedUploadWithProgress(
    `/portal/chats/${chatId}/attachments`,
    form,
    onProgress,
  )
  return parseJsonOrThrowApi(res)
}

export async function pinMessage(chatId: string, messageId: string): Promise<ChatMessage> {
  const res = await authenticatedFetch(`/portal/chats/${chatId}/messages/${messageId}/pin`, {
    method: 'POST',
  })
  return parseJsonOrThrowApi(res)
}

export async function unpinMessage(chatId: string, messageId: string): Promise<ChatMessage> {
  const res = await authenticatedFetch(`/portal/chats/${chatId}/messages/${messageId}/pin`, {
    method: 'DELETE',
  })
  return parseJsonOrThrowApi(res)
}

export async function listPinnedMessages(chatId: string): Promise<ChatMessage[]> {
  const res = await authenticatedFetch(`/portal/chats/${chatId}/messages/pinned`)
  return parseJsonOrThrowApi(res)
}

export type ChatAttachmentKind = 'media' | 'audio' | 'file'

export async function listChatAttachments(
  chatId: string,
  params?: { kind?: ChatAttachmentKind; skip?: number; limit?: number },
): Promise<PagedResponse<ChatAttachment>> {
  const qs = new URLSearchParams()
  if (params?.kind) qs.set('kind', params.kind)
  if (params?.skip !== undefined) qs.set('skip', String(params.skip))
  if (params?.limit !== undefined) qs.set('limit', String(params.limit))
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`/portal/chats/${chatId}/attachments${query}`)
  return parseJsonOrThrowApi(res)
}

export async function transcribeAttachment(
  chatId: string,
  attachmentId: string,
): Promise<ChatAttachment> {
  const res = await authenticatedFetch(`/portal/chats/${chatId}/attachments/${attachmentId}/transcribe`, {
    method: 'POST',
  })
  return parseJsonOrThrowApi(res)
}

export async function getMessageReaders(
  chatId: string,
  messageId: string,
): Promise<MessageReaderItem[]> {
  const res = await authenticatedFetch(
    `/portal/chats/${chatId}/messages/${messageId}/readers`,
  )
  const data = await parseJsonOrThrowApi<{ message_id: string; readers: MessageReaderItem[] }>(res)
  return data.readers
}

export async function getMessageReactionReactors(
  chatId: string,
  messageId: string,
  emoji: string,
): Promise<MessageReactorItem[]> {
  const qs = new URLSearchParams({ emoji })
  const res = await authenticatedFetch(
    `/portal/chats/${chatId}/messages/${messageId}/reactions/reactors?${qs}`,
  )
  const data = await parseJsonOrThrowApi<{
    message_id: string
    emoji: string
    reactors: MessageReactorItem[]
  }>(res)
  return data.reactors
}

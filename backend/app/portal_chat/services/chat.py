"""Публичный API сервисного слоя portal_chat.

Реэкспортирует всё из _queries*, _mutations* и group_chat,
чтобы внешний код (routes, тесты) мог импортировать из одного модуля.
"""

from app.portal_chat.services._mutations import (
    delete_message_for_all,
    delete_message_for_user,
    post_message,
    update_message,
)
from app.portal_chat.services._mutations_chats import (
    create_chat,
    get_or_create_direct_chat,
    mark_chat_read,
)
from app.portal_chat.services._mutations_forward import forward_chat_message
from app.portal_chat.services._mutations_pin import (
    list_pinned_messages,
    pin_message,
    unpin_message,
)
from app.portal_chat.services._mutations_reactions import toggle_message_reaction
from app.portal_chat.services._queries import (
    ensure_chat_access,
    ensure_chat_read_access,
    ensure_chat_write_access,
    get_batch_unread_counts,
    get_unread_counts_for_chat_members,
    list_chat_members,
    list_chats_for_user,
    user_can_access_message,
    user_is_chat_member,
)
from app.portal_chat.services._queries_attachments import list_chat_attachments
from app.portal_chat.services._queries_messages import (
    get_message_reaction_reactors,
    get_message_readers,
    list_messages,
    message_to_read,
    message_to_read_for_viewer,
    messages_to_read_for_viewer,
    search_messages_for_user,
)
from app.portal_chat.services.group_chat import (
    add_member_to_group_chat,
    patch_group_chat_title,
    remove_member_from_group_chat,
)
from app.portal_chat.services.transcription import transcribe_voice_attachment

__all__ = [
    "add_member_to_group_chat",
    "create_chat",
    "delete_message_for_all",
    "delete_message_for_user",
    "forward_chat_message",
    "ensure_chat_access",
    "ensure_chat_read_access",
    "ensure_chat_write_access",
    "get_batch_unread_counts",
    "get_unread_counts_for_chat_members",
    "get_message_readers",
    "get_message_reaction_reactors",
    "get_or_create_direct_chat",
    "list_chat_attachments",
    "list_chat_members",
    "list_chats_for_user",
    "list_messages",
    "list_pinned_messages",
    "mark_chat_read",
    "message_to_read",
    "patch_group_chat_title",
    "message_to_read_for_viewer",
    "messages_to_read_for_viewer",
    "pin_message",
    "post_message",
    "remove_member_from_group_chat",
    "toggle_message_reaction",
    "unpin_message",
    "search_messages_for_user",
    "transcribe_voice_attachment",
    "update_message",
    "user_can_access_message",
    "user_is_chat_member",
]

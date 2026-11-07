"""WebSocket-инфраструктура: одноразовые тикеты и менеджеры подключений.

Модули:
- ``room_manager`` — ``TopicRoomManager`` + Redis-канальные префиксы и TASK_BOARD_ROOM_ID
- ``managers`` — синглтоны ``TopicRoomManager`` для всех топиков (чаты, комментарии, доска задач и т.д.)
- ``inbox_manager`` — ``InboxManager`` для per-user WS inbox
- ``tickets`` — одноразовые WS-тикеты (Redis / in-memory)
"""

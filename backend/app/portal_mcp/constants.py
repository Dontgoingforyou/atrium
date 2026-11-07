"""Пределы списков и вложений MCP. Сервис получает уже ограниченный ``limit``."""

LIST_LIMIT_MAX = 200
LIST_LIMIT_DEFAULT = 50
# JSON-RPC не тянет доменный потолок вложения (2 ГБ): тело запроса держим в памяти.
MCP_FILE_MAX_BYTES = 8 * 1024 * 1024
# Base64 больше сырого файла, плюс конверт JSON-RPC. Иначе SDK ответит 413 раньше тула.
MCP_HTTP_BODY_MAX_BYTES = (MCP_FILE_MAX_BYTES + 2) // 3 * 4 + 65_536

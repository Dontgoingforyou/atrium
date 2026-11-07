def extract_groups_from_claim(payload: dict[str, object], claim_path: str) -> list[str]:
    """
    claim_path — точки как разделитель вложенности, последний сегмент — список или строка.
    Пример: "groups", "realm_access.roles".
    """
    parts = [p for p in claim_path.split(".") if p]
    if not parts:
        return []
    cur: object = payload
    for p in parts:
        if not isinstance(cur, dict):
            return []
        cur = cur.get(p)
    if isinstance(cur, str):
        return [cur]
    if isinstance(cur, list):
        return [str(x) for x in cur]
    return []

"""Локальные векторы по словам, когда ключ модели не задан.

Слова и пары соседних слов хешируются в фиксированную размерность и
нормируются. Косинусная близость тогда отражает общие слова, без внешнего API.
"""

from __future__ import annotations

import hashlib
import math
import re

_TOKEN = re.compile(r"[0-9a-zа-яё]+", re.IGNORECASE)
# Длинные окончания раньше коротких, иначе «ами» съест «иями».
_SUFFIXES = (
    "иями",
    "ями",
    "ами",
    "ого",
    "ему",
    "ыми",
    "ими",
    "ах",
    "ях",
    "ов",
    "ев",
    "ам",
    "ям",
    "ом",
    "ем",
    "ой",
    "ый",
    "ий",
    "ая",
    "яя",
    "ое",
    "ее",
    "ые",
    "ие",
    "ую",
    "юю",
    "а",
    "я",
    "ы",
    "и",
    "у",
    "ю",
    "е",
    "о",
)

# Общие слова в коротком учебном тексте дают косинус около 0.3, порог модели выше.
LOCAL_SEMANTIC_MIN_SCORE = 0.2


def _stem(token: str) -> str:
    word = token.lower().replace("ё", "е")
    if len(word) < 5:
        return word
    for suffix in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def local_embedding(text: str, dimension: int) -> list[float]:
    """Вектор размерности ``dimension``. Пустой текст — нули."""
    folded = text.lower().replace("ё", "е")
    tokens = [_stem(token) for token in _TOKEN.findall(folded)]
    tokens = [token for token in tokens if token]
    vector = [0.0] * dimension
    if not tokens or dimension <= 0:
        return vector
    features = list(tokens)
    features.extend(f"{left}_{right}" for left, right in zip(tokens, tokens[1:], strict=False))
    for feature in features:
        digest = hashlib.blake2b(feature.encode(), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "little") % dimension
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[bucket] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]

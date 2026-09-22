"""Stable, named randomness. No Python hash(), global RNG, or traversal counters."""
from __future__ import annotations
import hashlib
import json
import math
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any


def canonical(value: Any) -> str:
    def default(obj: Any) -> Any:
        if isinstance(obj, Enum):
            return obj.value
        if is_dataclass(obj):
            return asdict(obj)
        if isinstance(obj, (set, frozenset)):
            return sorted(obj)
        raise TypeError(f"Not JSON-compatible: {type(obj).__name__}")
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False, default=default)


def digest(*parts: Any, size: int = 16) -> str:
    return hashlib.blake2b(canonical(parts).encode('utf8'), digest_size=size,
                           person=b'PW-v1').hexdigest()


def derive_seed(parent: int | str, *names: Any) -> int:
    return int(digest(parent, *names, size=8), 16)


def stable_id(parent: str, type_id: str, key: Any) -> str:
    return f'{type_id}:{digest(parent, type_id, key, size=12)}'


class RandomStream:
    """Stateless samples: adding a named draw cannot perturb other draws."""
    __slots__ = ('seed',)
    def __init__(self, seed: int | str, *path: Any):
        self.seed = derive_seed(seed, *path)

    def unit(self, *key: Any) -> float:
        # Exactly 53 random bits, always in [0, 1).
        return (derive_seed(self.seed, *key) >> 11) / (1 << 53)

    def uniform(self, low: float, high: float, *key: Any) -> float:
        if not math.isfinite(low + high) or high < low:
            raise ValueError('Invalid uniform range')
        return low + (high-low) * self.unit(*key)

    def integer(self, low: int, high: int, *key: Any) -> int:
        if high < low:
            raise ValueError('Empty integer range')
        return low + int(self.unit(*key) * (high-low+1))

    def choice(self, values: tuple | list, *key: Any) -> Any:
        if not values:
            raise ValueError('Cannot choose from an empty sequence')
        return values[self.integer(0, len(values)-1, *key)]

    def branch(self, *key: Any) -> 'RandomStream':
        return RandomStream(self.seed, *key)

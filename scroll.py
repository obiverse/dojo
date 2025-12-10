#!/usr/bin/env python3
"""
Scroll - 9S Protocol Compatible

The universal data envelope. All data in 9S is wrapped in a Scroll.

Scroll := {
    key:  string        // Path in namespace (e.g., "/mind/oioi/knowledge/go")
    data: any           // Payload (JSON-serializable)
    meta: Meta | null   // Optional metadata
}

Meta := {
    schema:  string     // Type identifier (e.g., "9s/knowledge", "dojo/ninja")
    version: uint64     // Increments on each write
    hash:    string     // SHA-256 hex of key + JSON(data)
    time:    int64      // Unix timestamp in milliseconds
}

Beyond micrograd:
- Tracks computation lineage via `meta.prev` (extension)
- Computes `meta.influence` for backpropagation (extension)
- Works with ANY data type, not just numbers
"""

from typing import Any, Callable, List, Dict, Optional, Union
from dataclasses import dataclass, field
import time
import json
import hashlib


@dataclass
class Meta:
    """
    9S Scroll metadata.

    Standard fields from protocol:
    - schema: Type identifier
    - version: Increments on write
    - hash: Content-addressable identity
    - time: Unix timestamp in ms

    Extensions for computation:
    - prev: Parent scroll keys (lineage)
    - op: Operation that created this scroll
    - influence: Gradient analog (for backprop)
    """
    schema: str = "dojo/scroll"
    version: int = 1
    hash: str = ""
    time: int = field(default_factory=lambda: int(time.time() * 1000))

    # Extensions for computation graph
    prev: List[str] = field(default_factory=list)
    op: str = ""
    influence: float = 0.0

    def to_dict(self) -> Dict:
        """Serialize to 9S wire format."""
        d = {
            "schema": self.schema,
            "version": self.version,
            "hash": self.hash,
            "time": self.time,
        }
        # Only include extensions if non-default
        if self.prev:
            d["prev"] = self.prev
        if self.op:
            d["op"] = self.op
        if self.influence != 0.0:
            d["influence"] = self.influence
        return d

    @classmethod
    def from_dict(cls, d: Dict) -> 'Meta':
        return cls(
            schema=d.get("schema", "dojo/scroll"),
            version=d.get("version", 1),
            hash=d.get("hash", ""),
            time=d.get("time", int(time.time() * 1000)),
            prev=d.get("prev", []),
            op=d.get("op", ""),
            influence=d.get("influence", 0.0),
        )


class Scroll:
    """
    Universal value primitive - 9S Protocol compatible.

    Features:
    - Path-based identity (Plan 9 style)
    - Metadata tracks provenance
    - Data can be ANY JSON-serializable type
    - Operations track lineage via meta.prev
    - Backpropagation computes influence

    Usage:
        # Create with explicit key
        s = Scroll("/compute/a", 2.0)

        # Create with auto-generated key
        s = Scroll(data={"client": "Acme"})

        # Arithmetic (creates new scrolls with lineage)
        c = a * b + a ** 2

        # Backpropagate influence
        c.backward()

        # Serialize for 9S
        wire = s.to_dict()
    """

    # Class registry for key lookups (mini namespace)
    _registry: Dict[str, 'Scroll'] = {}

    def __init__(
        self,
        key_or_data: Union[str, Any] = None,
        data: Any = None,
        meta: Optional[Meta] = None,
    ):
        """
        Create a scroll.

        Args:
            key_or_data: Either a path string OR the data (if no key)
            data: The payload (if key_or_data is a path)
            meta: Optional metadata
        """
        # Handle both Scroll(key, data) and Scroll(data)
        if isinstance(key_or_data, str) and key_or_data.startswith("/"):
            self.key = key_or_data
            self.data = data
        else:
            self.data = key_or_data if data is None else data
            self.key = self._generate_key(self.data)

        # Initialize or use provided meta
        self.meta = meta or Meta()

        # Compute hash if not provided
        if not self.meta.hash:
            self.meta.hash = self._compute_hash()

        # For backpropagation
        self._backward: Callable[[], None] = lambda: None

        # Register for lookups
        Scroll._registry[self.key] = self

    def _generate_key(self, data: Any) -> str:
        """Generate unique key from data hash + timestamp."""
        h = hashlib.sha256(str(data).encode()).hexdigest()[:8]
        t = int(time.time() * 1000) % 100000
        return f"/scroll/{h}_{t}"

    def _compute_hash(self) -> str:
        """Compute SHA-256 hash of key + data (9S spec)."""
        content = self.key + json.dumps(self.data, default=str, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 9S NAMESPACE OPERATIONS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @classmethod
    def read(cls, key: str) -> Optional['Scroll']:
        """Read a scroll by key (9S Read operation)."""
        return cls._registry.get(key)

    @classmethod
    def list(cls, prefix: str = "/") -> List[str]:
        """List paths under prefix (9S List operation)."""
        return [k for k in cls._registry.keys() if k.startswith(prefix)]

    @classmethod
    def clear(cls):
        """Clear the registry (for testing)."""
        cls._registry = {}

    def to_dict(self) -> Dict:
        """Serialize to 9S wire format."""
        return {
            "key": self.key,
            "data": self.data if self._is_json_safe(self.data) else str(self.data),
            "meta": self.meta.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: Dict) -> 'Scroll':
        """Deserialize from 9S wire format."""
        meta = Meta.from_dict(d.get("meta", {}))
        return cls(d["key"], d["data"], meta)

    @staticmethod
    def _is_json_safe(obj: Any) -> bool:
        try:
            json.dumps(obj)
            return True
        except (TypeError, ValueError):
            return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # COMPUTATION GRAPH OPERATIONS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _child(self, data: Any, op: str, parents: List['Scroll']) -> 'Scroll':
        """Create a child scroll that tracks its parents."""
        meta = Meta(
            schema="dojo/computed",
            version=1,
            prev=[p.key for p in parents],
            op=op,
        )
        return Scroll(data=data, meta=meta)

    def __add__(self, other: 'Scroll | Any') -> 'Scroll':
        other = other if isinstance(other, Scroll) else Scroll(other)

        # Type-aware addition
        if isinstance(self.data, (int, float)) and isinstance(other.data, (int, float)):
            result = self.data + other.data
        elif isinstance(self.data, str) and isinstance(other.data, str):
            result = self.data + other.data
        elif isinstance(self.data, list) and isinstance(other.data, list):
            result = self.data + other.data
        elif isinstance(self.data, dict) and isinstance(other.data, dict):
            result = {**self.data, **other.data}
        else:
            result = self.data + other.data

        out = self._child(result, '+', [self, other])

        def _backward():
            if isinstance(self.data, (int, float)):
                self.meta.influence += out.meta.influence
                other.meta.influence += out.meta.influence
        out._backward = _backward

        return out

    def __radd__(self, other: Any) -> 'Scroll':
        return self.__add__(other)

    def __mul__(self, other: 'Scroll | Any') -> 'Scroll':
        other = other if isinstance(other, Scroll) else Scroll(other)

        if isinstance(self.data, (int, float)) and isinstance(other.data, (int, float)):
            result = self.data * other.data
        elif isinstance(self.data, str) and isinstance(other.data, int):
            result = self.data * other.data
        elif isinstance(self.data, list) and isinstance(other.data, int):
            result = self.data * other.data
        else:
            result = self.data * other.data

        out = self._child(result, '*', [self, other])

        def _backward():
            if isinstance(self.data, (int, float)) and isinstance(other.data, (int, float)):
                self.meta.influence += other.data * out.meta.influence
                other.meta.influence += self.data * out.meta.influence
        out._backward = _backward

        return out

    def __rmul__(self, other: Any) -> 'Scroll':
        return self.__mul__(other)

    def __pow__(self, n: Union[int, float]) -> 'Scroll':
        out = self._child(self.data ** n, f'**{n}', [self])

        def _backward():
            self.meta.influence += n * (self.data ** (n - 1)) * out.meta.influence
        out._backward = _backward

        return out

    def __neg__(self) -> 'Scroll':
        return self * -1

    def __sub__(self, other: 'Scroll | Any') -> 'Scroll':
        return self + (-other if isinstance(other, Scroll) else Scroll(-other))

    def __truediv__(self, other: 'Scroll | Any') -> 'Scroll':
        return self * (other ** -1 if isinstance(other, Scroll) else Scroll(other) ** -1)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # UNIVERSAL OPERATIONS (beyond numbers)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def transform(self, fn: Callable[[Any], Any], op_name: str = "lambda") -> 'Scroll':
        """Apply any function, track lineage."""
        return self._child(fn(self.data), op_name, [self])

    def map(self, fn: Callable[[Any], Any]) -> 'Scroll':
        """Map over iterable data."""
        if hasattr(self.data, '__iter__') and not isinstance(self.data, (str, dict)):
            return self._child([fn(x) for x in self.data], 'map', [self])
        return self.transform(fn, 'map')

    def filter(self, predicate: Callable[[Any], bool]) -> 'Scroll':
        """Filter iterable data."""
        if hasattr(self.data, '__iter__') and not isinstance(self.data, (str, dict)):
            return self._child([x for x in self.data if predicate(x)], 'filter', [self])
        return self

    def reduce(self, fn: Callable[[Any, Any], Any], initial: Any = None) -> 'Scroll':
        """Reduce iterable data."""
        if hasattr(self.data, '__iter__') and not isinstance(self.data, (str, dict)):
            from functools import reduce as functools_reduce
            result = functools_reduce(fn, self.data, initial) if initial else functools_reduce(fn, self.data)
            return self._child(result, 'reduce', [self])
        return self

    def get(self, key: Union[str, int]) -> 'Scroll':
        """Extract field from dict or list."""
        if isinstance(self.data, dict):
            return self._child(self.data.get(key), f'.{key}', [self])
        elif isinstance(self.data, (list, tuple)) and isinstance(key, int):
            return self._child(self.data[key] if key < len(self.data) else None, f'[{key}]', [self])
        return self._child(None, f'.{key}', [self])

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ACTIVATIONS (neural computation)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def relu(self) -> 'Scroll':
        out = self._child(max(0, self.data) if isinstance(self.data, (int, float)) else self.data, 'relu', [self])

        def _backward():
            if isinstance(out.data, (int, float)):
                self.meta.influence += (out.data > 0) * out.meta.influence
        out._backward = _backward

        return out

    def tanh(self) -> 'Scroll':
        import math
        if isinstance(self.data, (int, float)):
            t = math.tanh(self.data)
            out = self._child(t, 'tanh', [self])

            def _backward():
                self.meta.influence += (1 - t * t) * out.meta.influence
            out._backward = _backward

            return out
        return self

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # BACKPROPAGATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def backward(self):
        """Backpropagate influence through the computation graph."""
        topo = []
        visited = set()

        def build_topo(scroll):
            if scroll.key not in visited:
                visited.add(scroll.key)
                for prev_key in scroll.meta.prev:
                    prev = Scroll.read(prev_key)
                    if prev:
                        build_topo(prev)
                topo.append(scroll)

        build_topo(self)

        self.meta.influence = 1.0
        for scroll in reversed(topo):
            scroll._backward()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # LINEAGE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def lineage(self, depth: int = 10) -> List[Dict]:
        """Trace computation history."""
        history = []

        def trace(scroll, d):
            if d <= 0 or not scroll:
                return
            history.append({
                "key": scroll.key,
                "op": scroll.meta.op,
                "data": str(scroll.data)[:30],
                "influence": scroll.meta.influence,
            })
            for prev_key in scroll.meta.prev:
                trace(Scroll.read(prev_key), d - 1)

        trace(self, depth)
        return history

    def __repr__(self) -> str:
        data_str = str(self.data)[:30]
        return f"Scroll({self.key}, {data_str})"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DEMO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def demo():
    print("=" * 60)
    print("SCROLL - 9S Protocol Compatible")
    print("=" * 60)

    Scroll.clear()

    # 1. Create with 9S-style key
    print("\n[1] 9S WIRE FORMAT")
    invoice = Scroll("/cache/invoices/001", {"client": "Acme", "amount": 500})
    print(f"  Scroll: {invoice}")
    print(f"  Wire format:")
    print(json.dumps(invoice.to_dict(), indent=4))

    # 2. Numeric computation with lineage
    print("\n[2] COMPUTATION GRAPH")
    a = Scroll("/compute/a", 2.0)
    b = Scroll("/compute/b", 3.0)
    c = a * b + a ** 2  # c = 6 + 4 = 10
    c.backward()

    print(f"  a = {a.data}, influence = {a.meta.influence}")
    print(f"  b = {b.data}, influence = {b.meta.influence}")
    print(f"  c = a*b + a² = {c.data}")

    # 3. String/Dict/List operations
    print("\n[3] UNIVERSAL TYPES")
    s1 = Scroll(data="Hello ")
    s2 = Scroll(data="World")
    s3 = s1 + s2
    print(f"  String: {s1.data!r} + {s2.data!r} = {s3.data!r}")

    d1 = Scroll(data={"a": 1})
    d2 = Scroll(data={"b": 2})
    d3 = d1 + d2
    print(f"  Dict: {d1.data} + {d2.data} = {d3.data}")

    l1 = Scroll(data=[1, 2])
    l2 = Scroll(data=[3, 4])
    l3 = l1 + l2
    print(f"  List: {l1.data} + {l2.data} = {l3.data}")

    # 4. Namespace operations
    print("\n[4] NAMESPACE (mini 9S)")
    print(f"  List(/): {Scroll.list('/')[:5]}...")
    print(f"  Read(/compute/a): {Scroll.read('/compute/a')}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    demo()

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from .errors import AIProviderUnavailable


@dataclass(frozen=True)
class ModelChain:
    """Ordered list of model names with a self-healing 'active' head.

    On startup, .resolve() filters the chain against what the provider's API
    actually exposes, returning the first survivor as active.

    On persistent 404 ('model not found'), .demote() drops the active head
    and promotes the next survivor.
    """

    chain: tuple[str, ...]
    active: str
    provider: str = field(default="?")

    @classmethod
    def resolve(
        cls, available: set[str], chain: Sequence[str], *, provider: str = "?"
    ) -> "ModelChain":
        for m in chain:
            if m in available:
                return cls(chain=tuple(chain), active=m, provider=provider)
        raise AIProviderUnavailable(
            f"no model in chain is available (chain={list(chain)}, available={sorted(available)})",
            provider=provider,
        )

    def demote(self) -> "ModelChain":
        remaining = tuple(m for m in self.chain if m != self.active)
        if not remaining:
            raise AIProviderUnavailable("chain exhausted", provider=self.provider)
        return ModelChain(chain=remaining, active=remaining[0], provider=self.provider)

"""Provider registry for looking up data providers by name."""

from __future__ import annotations

from portfolio_simulator.providers.base import DataProvider


class ProviderRegistry:
    """Registry mapping provider names to instances."""

    def __init__(self) -> None:
        self._providers: dict[str, DataProvider] = {}
        self._default_name: str | None = None

    def register(self, provider: DataProvider, *, default: bool = False) -> None:
        self._providers[provider.name] = provider
        if default or self._default_name is None:
            self._default_name = provider.name

    def get(self, name: str) -> DataProvider:
        if name not in self._providers:
            raise KeyError(f"Provider '{name}' not registered. Available: {list(self._providers)}")
        return self._providers[name]

    @property
    def default(self) -> DataProvider:
        if self._default_name is None:
            raise RuntimeError("No providers registered")
        return self._providers[self._default_name]

    @property
    def available(self) -> list[str]:
        return list(self._providers.keys())

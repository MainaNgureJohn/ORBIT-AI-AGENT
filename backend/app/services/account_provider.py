"""Provider contract for authenticated, read-only account snapshots."""

from collections.abc import Awaitable, Sequence
from typing import Protocol

from app.models.schemas import AccountSnapshot


class AccountProviderError(RuntimeError):
    """Base error for safe account reads."""


class AccountCredentialsError(AccountProviderError):
    pass


class AccountPermissionError(AccountProviderError):
    pass


class AccountDataUnavailableError(AccountProviderError):
    pass


class AccountProvider(Protocol):
    async def get_account(self) -> AccountSnapshot:
        """Return a verified read-only account snapshot."""

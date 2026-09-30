from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class AccountState:
    initial_cash: Decimal
    cash: Decimal
    realized_pnl: Decimal
    reserved_cash: Decimal


class PaperAccount:
    def __init__(
        self,
        initial_cash: Decimal,
    ):
        if initial_cash <= 0:
            raise ValueError("initial_cash must be > 0")

        self._initial_cash = initial_cash
        self._cash = initial_cash
        self._realized_pnl = Decimal("0")
        self._reserved_cash = Decimal("0")

    @property
    def initial_cash(self) -> Decimal:
        return self._initial_cash

    @property
    def cash(self) -> Decimal:
        return self._cash

    @property
    def realized_pnl(self) -> Decimal:
        return self._realized_pnl

    @property
    def reserved_cash(self) -> Decimal:
        return self._reserved_cash

    @property
    def available_cash(self) -> Decimal:
        return self._cash - self._reserved_cash

    def reserve_cash(
        self,
        amount: Decimal,
    ) -> None:
        if amount <= 0:
            raise ValueError("amount must be > 0")

        if amount > self.available_cash:
            raise ValueError("insufficient available cash")

        self._reserved_cash += amount

    def release_cash(
        self,
        amount: Decimal,
    ) -> None:
        if amount <= 0:
            raise ValueError("amount must be > 0")

        if amount > self._reserved_cash:
            raise ValueError("cannot release more than reserved cash")

        self._reserved_cash -= amount

    def apply_realized_pnl(
        self,
        pnl: Decimal,
    ) -> None:
        self._cash += pnl
        self._realized_pnl += pnl

        if self._cash < 0:
            raise ValueError("account cash cannot become negative")

    def state(self) -> AccountState:
        return AccountState(
            initial_cash=self._initial_cash,
            cash=self._cash,
            realized_pnl=self._realized_pnl,
            reserved_cash=self._reserved_cash,
        )

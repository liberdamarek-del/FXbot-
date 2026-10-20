from decimal import Decimal

from src.paper_account import PaperAccount


account = PaperAccount(
    initial_cash=Decimal("10000")
)

assert account.initial_cash == Decimal("10000")
assert account.cash == Decimal("10000")
assert account.realized_pnl == Decimal("0")
assert account.reserved_cash == Decimal("0")
assert account.available_cash == Decimal("10000")

account.reserve_cash(Decimal("1000"))

assert account.reserved_cash == Decimal("1000")
assert account.available_cash == Decimal("9000")

account.release_cash(Decimal("400"))

assert account.reserved_cash == Decimal("600")
assert account.available_cash == Decimal("9400")

account.apply_realized_pnl(Decimal("125.50"))

assert account.cash == Decimal("10125.50")
assert account.realized_pnl == Decimal("125.50")
assert account.available_cash == Decimal("9525.50")

account.apply_realized_pnl(Decimal("-25.50"))

assert account.cash == Decimal("10100.00")
assert account.realized_pnl == Decimal("100.00")

state = account.state()

assert state.initial_cash == Decimal("10000")
assert state.cash == Decimal("10100.00")
assert state.realized_pnl == Decimal("100.00")
assert state.reserved_cash == Decimal("600")


print("=" * 60)
print("M4.1 PAPER ACCOUNT")
print("=" * 60)
print(f"INITIAL CASH: {account.initial_cash}")
print(f"CASH: {account.cash}")
print(f"REALIZED PNL: {account.realized_pnl}")
print(f"RESERVED CASH: {account.reserved_cash}")
print(f"AVAILABLE CASH: {account.available_cash}")

print("INITIALIZATION: PASS")
print("CASH MANAGEMENT: PASS")
print("RESERVATION: PASS")
print("RELEASE: PASS")
print("REALIZED PNL: PASS")
print("STATE SNAPSHOT: PASS")
print("DECIMAL PRECISION: PASS")
print("RESULT: PASS")
print("=" * 60)

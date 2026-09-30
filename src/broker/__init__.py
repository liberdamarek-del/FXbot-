"""Broker adapters (modules 11, 12, 64: the execution-truth layer).

A broker adapter is the ONLY way a quote becomes BROKER_TRUTH with real
bid/ask (execution state EXECUTABLE). Without one, every price in the
system is a public MODEL-PRICE and the run certificate says
BROKER-BLOCKED.

    base.py    the interface every adapter implements
    paper.py   paper account computed from the immutable prediction ledger
    oanda.py   OANDA v20 REST: read-only quotes (bid/ask) and account
               summary. Needs a token; NOT tested from this project
               (ENV-UNVERIFIED) - test it together before relying on it.
    xtb.py     placeholder: XTB's legacy xAPI was switched off on
               2025-03-14, no public replacement is known

Order execution with a real broker is OUT OF SCOPE of this project phase
(PROJECT_STATE rules); adapters are read-only. See README "Pripojeni
brokera" for how to add one.
"""

import os


def from_env():
    """Adapter selected by FXBOT_BROKER (none / oanda). Returns None when
    no broker is configured."""
    name = os.getenv("FXBOT_BROKER", "").strip().lower()

    if name in ("", "none"):
        return None

    if name == "oanda":
        from src.broker.oanda import OandaBroker

        return OandaBroker.from_env()

    if name == "xtb":
        from src.broker.xtb import XtbBroker

        return XtbBroker()

    raise ValueError(f"unknown FXBOT_BROKER={name!r} (none, oanda, xtb)")

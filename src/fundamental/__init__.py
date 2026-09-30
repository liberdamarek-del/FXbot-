"""Fundamental layer (specification modules 17-33, 47).

store.py      point-in-time storage (value + when it became publicly known)
catalog.py    which series describe which currency, with source and lag
adapters.py   downloads and parsers for the public sources (keyless)
calendar.py   economic calendar snapshots (event risk, module 47)
engine.py     per-currency and per-pair evidence (rates, yields, carry,
              positioning, risk, commodities, events)
"""

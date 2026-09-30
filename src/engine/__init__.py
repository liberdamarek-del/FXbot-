"""Analytic engine of the V7.8.0 implementation.

The SAME code serves the live run and the backtest (module 74: the
benchmark and the model see the same history, costs and rules):

series.py      price series with causal indicators, point-in-time access
params.py      every provisional threshold in one versioned place
technical.py   multi-timeframe technical view D1 / H4 / H1 (modules 42-49)
fundamental.py per-pair fundamental evidence (modules 17-33, 36)
regime.py      regime and change-point diagnosis (modules 40, 41)
decision.py    evidence matrix, hypotheses, gates, entry/SL/TP (37, 45-58)
portfolio.py   Top-3, factor concentration, risk sizing (57, 58, 141)
thesis.py      persistent thesis state, no-instant-flip (138-141)
"""

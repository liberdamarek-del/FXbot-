"""V7.8.0 run procedure (specification module 145) and its artifacts.

manifest.py     module manifest 0-145 with implementation status, model
                fingerprint, Word document verification (modules 101, 114)
runstate.py     run state machine, execution trace (modules 103, 105)
quotes.py       quote contract, observation classes, freshness, skew,
                conflict/outlier, closed-market mode (modules 117-120, 132-135)
coverage.py     path coverage certificate, between-run delta (92, 106, 123, 137)
sources.py      source register with runtime capability states (9, 116, 125, 129)
audit.py        due-outcome audit of locked predictions (61, 62, 81)
persist.py      artifacts, staged commit, read-back (99, 104, 124)
report.py       Czech user output + certificates (7, 84, 85, 113, 135, 141)
run.py          the orchestrator
"""

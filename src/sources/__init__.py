"""Data source adapters (RAW -> NORMALIZED -> VALIDATED, module 9).

Every adapter keeps the exact payload it received (module 124) and records
every attempt (module 120). None of them invents a value when a source
fails: the caller gets an explicit error / GAP state instead.
"""

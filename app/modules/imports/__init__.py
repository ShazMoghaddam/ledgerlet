"""Imports module: turn a bank statement CSV into transactions, in two steps.

1. preview  - parse the file, flag invalid rows and duplicates, save nothing
2. confirm  - the landlord picks rows and categories; those become transactions

This module owns no tables. It works entirely through the public services of
the properties and transactions modules.

Files:
    parser.py        pure CSV parsing (bytes in, rows out)
    fingerprint.py   stable identity for a bank row, used for dedup
    schemas.py       request/response contract
    service.py       the two-step workflow and its rules
    router.py        HTTP endpoints
    dependencies.py  wiring
"""

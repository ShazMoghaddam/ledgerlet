"""Tax module: turns recorded transactions into the figures HMRC asks for.

Owns no tables. Reads properties and transactions through their services.

Files:
    periods.py       tax years, update periods and deadlines (pure date logic)
    calculations.py  ownership shares and category totals (pure arithmetic)
    schemas.py       response shapes
    service.py       builds year-to-date summaries and obligation lists
    router.py        HTTP endpoints
    dependencies.py  wiring
"""

"""HMRC module: the landlord's connection to HMRC, and (next) submissions.

Two separate sign-ins exist in LedgerLet:
- the landlord signs in to LedgerLet (core/auth.py, landlords module)
- the landlord authorises LedgerLet with HMRC (this module), using OAuth 2.0

Files:
    crypto.py        encrypts HMRC tokens at rest; seals the OAuth state
    oauth.py         talks to HMRC's token endpoint (behind a Protocol)
    models.py        one HMRC connection per landlord
    repository.py    SQL
    service.py       connect, refresh, disconnect
    router.py        /hmrc/connect, /hmrc/callback, /hmrc/connection
"""

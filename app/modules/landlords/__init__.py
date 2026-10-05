"""Landlords module: LedgerLet's own record of each signed-in user.

The identity provider proves who someone is (core/auth.py). This module keeps
what LedgerLet needs to know about them: their settings, and the id every
property hangs off. A landlord row is created automatically on first sign-in.
"""

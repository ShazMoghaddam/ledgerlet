"""Transactions module: money in and out, per property.

Same four layers as properties (router -> service -> repository -> models).
It talks to the properties module only through PropertyService, never by
querying the properties table itself, so the module boundary stays clean.
"""

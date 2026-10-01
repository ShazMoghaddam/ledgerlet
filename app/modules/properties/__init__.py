"""Properties module: the rental properties a landlord owns.

Layers, top to bottom (each only talks to the one below):
    router.py      API layer        HTTP in, HTTP out
    service.py     Service layer    business rules
    repository.py  Repository layer database queries
    models.py      Data model       table definition

Supporting files:
    schemas.py       the module's contract (request/response shapes)
    validators.py    pure helpers, e.g. UK postcode normalisation
    dependencies.py  wires service + repository together per request
"""

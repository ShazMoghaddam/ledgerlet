"""Model registry: import every module's models here.

Alembic and the test suite import this file so SQLAlchemy knows about every
table. When you add a module with tables, add one import line below.
"""

from app.modules.properties.models import Property  # noqa: F401
from app.modules.transactions.models import Transaction  # noqa: F401

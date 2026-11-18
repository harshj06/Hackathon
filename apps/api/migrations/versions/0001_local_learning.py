"""Initial local learning schema, including pre-migration local installations."""
from alembic import op
from app.storage import Base

revision='0001'
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    Base.metadata.create_all(op.get_bind(),checkfirst=True)

def downgrade():
    raise RuntimeError('Destructive schema downgrade is intentionally disabled. Restore a reviewed backup instead.')

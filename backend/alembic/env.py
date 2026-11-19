from logging.config import fileConfig
from alembic import context
from sqlalchemy import create_engine
from app.config import settings
from app.database import Base
import app.models  # noqa: F401  (registers tables)

fileConfig(context.config.config_file_name)

if context.is_offline_mode():
    context.configure(url=settings.database_url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    with create_engine(settings.database_url).connect() as conn:
        context.configure(connection=conn, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()

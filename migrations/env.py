import logging
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')

def get_database_url():
    """Get database URL from environment or Flask app context"""
    url = config.get_main_option('sqlalchemy.url')
    if url and url != 'driver://user:pass@localhost/dbname':
        return url
    
    url = os.environ.get('PRODUCTION_DATABASE_URL') or os.environ.get('DATABASE_URL')
    if url:
        return url.replace('%', '%%')
    
    try:
        from flask import current_app
        if current_app:
            try:
                engine = current_app.extensions['migrate'].db.get_engine()
            except (TypeError, AttributeError):
                engine = current_app.extensions['migrate'].db.engine
            
            try:
                return engine.url.render_as_string(hide_password=False).replace('%', '%%')
            except AttributeError:
                return str(engine.url).replace('%', '%%')
    except (RuntimeError, KeyError):
        pass
    
    raise RuntimeError("No database URL found. Set DATABASE_URL or PRODUCTION_DATABASE_URL environment variable.")


def get_target_metadata():
    """Get SQLAlchemy metadata for migrations"""
    try:
        from flask import current_app
        if current_app:
            target_db = current_app.extensions['migrate'].db
            if hasattr(target_db, 'metadatas'):
                return target_db.metadatas[None]
            return target_db.metadata
    except (RuntimeError, KeyError):
        pass
    
    try:
        from app import db
        if hasattr(db, 'metadatas'):
            return db.metadatas[None]
        return db.metadata
    except ImportError:
        pass
    
    try:
        import models
        from sqlalchemy.orm import DeclarativeBase
        class Base(DeclarativeBase):
            pass
        return Base.metadata
    except ImportError:
        pass
    
    return None


database_url = get_database_url()
config.set_main_option('sqlalchemy.url', database_url)
target_metadata = get_target_metadata()


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, 
        target_metadata=target_metadata, 
        literal_binds=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""

    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    conf_args = {
        "process_revision_directives": process_revision_directives
    }
    
    try:
        from flask import current_app
        if current_app:
            migrate_conf = current_app.extensions.get('migrate')
            if migrate_conf and hasattr(migrate_conf, 'configure_args'):
                conf_args.update(migrate_conf.configure_args)
    except (RuntimeError, KeyError):
        pass

    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            **conf_args
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

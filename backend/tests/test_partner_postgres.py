"""Opt-in real PostgreSQL verification in a transaction-local temporary schema.

Only TEST_PARTNER_POSTGRES_URL is used. Never read DATABASE_URL/.env for this.
The supplied server must be a disposable test database, not production.
"""
import importlib.util
import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_postgres_partner_migration_and_sql_quota():
    url=os.getenv('TEST_PARTNER_POSTGRES_URL')
    if not url:pytest.skip('TEST_PARTNER_POSTGRES_URL missing; PostgreSQL partner check NOT executed')
    from app.db.base import Base
    from app.services.partner_security import quota,PartnerError
    engine=create_engine(url,hide_parameters=True)
    assert engine.dialect.name=='postgresql'
    with engine.connect() as connection:
        tx=connection.begin();schema='partner_test_'+uuid4().hex
        try:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            connection.exec_driver_sql(f'SET LOCAL search_path TO "{schema}"')
            Base.metadata.create_all(connection,tables=[t for t in Base.metadata.sorted_tables if not t.name.startswith('partner_')])
            path=Path(__file__).parents[1]/'alembic/versions/202611070001_partner_api_p0.py'
            spec=importlib.util.spec_from_file_location('partner_pg_migration',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
            with Operations.context(MigrationContext.configure(connection)):m.upgrade()
            assert 'partner_tokens' in inspect(connection).get_table_names()
            with Session(bind=connection,join_transaction_mode='create_savepoint') as db:
                quota(db,'test-client',1,1)
                with pytest.raises(PartnerError) as exc:quota(db,'test-client',1,1)
                assert exc.value.status==429
        finally:tx.rollback()
    engine.dispose()

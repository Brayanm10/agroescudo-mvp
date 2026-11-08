"""Fail-closed staging destination checks. Never infer a DB from production."""
import hashlib
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url


LABEL = 'AgroEscudo LEADY Staging'


def destination(config):
    if config.environment != 'staging':
        raise ValueError('Staging requiere ENVIRONMENT=staging.')
    url=make_url(config.database_url)
    expected=(config.partner_staging_expected_host,config.partner_staging_expected_database,config.partner_staging_expected_role)
    if not all(expected) or any('REPLACE' in x or '<' in x for x in expected):
        raise ValueError('Falta aprobar explícitamente host, base y rol exclusivos de staging.')
    if not url.drivername.startswith('postgresql') or (url.host,url.database,url.username)!=expected:
        raise ValueError('Destino no coincide con la configuración aprobada de staging.')
    if expected[1]!='leady_staging' or expected[2]!='leady_staging_role':
        raise ValueError('La base y el rol deben ser exclusivos: leady_staging / leady_staging_role.')
    if not url.host.startswith('ep-') or not url.host.endswith('.neon.tech'):
        raise ValueError('Se requiere un endpoint Neon explícito; no se permiten destinos inferidos.')
    if url.query.get('sslmode')!='verify-full':
        raise ValueError('Staging requiere sslmode=verify-full y CA confiable configurada.')
    return hashlib.sha256('|'.join(expected).encode()).hexdigest()


def check_connection(connection, config, initialize=False):
    fingerprint=destination(config)
    identity=connection.execute(text('SELECT current_database(), current_user')).one()
    if tuple(identity)!=(config.partner_staging_expected_database,config.partner_staging_expected_role):
        raise ValueError('La identidad efectiva de PostgreSQL no coincide con staging.')
    inspector=inspect(connection)
    tables=inspector.get_table_names(schema='public')
    for schema in inspector.get_schema_names():
        if schema not in ('public','information_schema') and not schema.startswith('pg_') and inspector.get_table_names(schema=schema):
            raise ValueError('Se detectaron tablas fuera del esquema staging esperado; no usar copias de producción.')
    if 'partner_staging_identity' not in tables:
        if not initialize or tables:
            raise ValueError('Destino no marcado como staging o base no vacía; no se ejecutan migraciones ni seed.')
        connection.execute(text('CREATE TABLE public.partner_staging_identity (label TEXT PRIMARY KEY, fingerprint TEXT NOT NULL)'))
        connection.execute(text('INSERT INTO public.partner_staging_identity (label,fingerprint) VALUES (:label,:fingerprint)'),{'label':LABEL,'fingerprint':fingerprint})
    rows=connection.execute(text('SELECT label, fingerprint FROM public.partner_staging_identity')).all()
    if [tuple(r) for r in rows]!=[(LABEL,fingerprint)]:
        raise ValueError('Identidad de staging inválida o copiada de otro endpoint.')


def engine_options():
    return {'hide_parameters':True,'pool_pre_ping':True,'pool_size':3,'max_overflow':2,'pool_timeout':3,
            'connect_args':{'connect_timeout':5,'options':'-c statement_timeout=5000 -c lock_timeout=2000 -c search_path=public'}}

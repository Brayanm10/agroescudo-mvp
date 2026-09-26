"""Add the pluviometry data core.

Revision ID: 202609240001
Revises: 202609060001
"""

from alembic import op
import sqlalchemy as sa


revision = "202609240001"
down_revision = "202609060001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("sites") as batch:
        batch.add_column(sa.Column("boundary_geojson", sa.JSON(), nullable=True))
    with op.batch_alter_table("storage_units") as batch:
        batch.add_column(sa.Column("boundary_geojson", sa.JSON(), nullable=True))
    with op.batch_alter_table("devices") as batch:
        batch.add_column(sa.Column("latitude", sa.Float(), nullable=True))
        batch.add_column(sa.Column("longitude", sa.Float(), nullable=True))
    with op.batch_alter_table("metric_definitions") as batch:
        batch.add_column(
            sa.Column(
                "aggregation_strategy",
                sa.String(length=24),
                nullable=False,
                server_default="avg",
            )
        )

    definitions = sa.table(
        "metric_definitions",
        sa.column("numeric_id", sa.Integer()),
        sa.column("metric_code", sa.String()),
        sa.column("display_name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("canonical_unit", sa.String()),
        sa.column("storage_type", sa.String()),
        sa.column("scale_factor", sa.Float()),
        sa.column("physical_min", sa.Float()),
        sa.column("physical_max", sa.Float()),
        sa.column("default_decimals", sa.Integer()),
        sa.column("default_chart_type", sa.String()),
        sa.column("aggregation_strategy", sa.String()),
        sa.column("product_compatibility", sa.String()),
        sa.column("client_visibility", sa.Boolean()),
        sa.column("is_derived", sa.Boolean()),
        sa.column("calibration_method", sa.String()),
        sa.column("alert_supported", sa.Boolean()),
        sa.column("display_order", sa.Integer()),
        sa.column("registry_version", sa.Integer()),
    )
    rows = [
        {
                "numeric_id": 16,
                "metric_code": "RAIN_DELTA_MM",
                "display_name": "Precipitacion incremental",
                "description": "Incremento de precipitacion desde la lectura anterior.",
                "canonical_unit": "mm",
                "storage_type": "float",
                "scale_factor": 1,
                "physical_min": 0,
                "physical_max": None,
                "default_decimals": 2,
                "default_chart_type": "bar",
                "aggregation_strategy": "sum",
                "product_compatibility": "RAIN_GAUGE",
                "client_visibility": True,
                "is_derived": False,
                "calibration_method": None,
                "alert_supported": True,
                "display_order": 160,
                "registry_version": 2,
        },
        {
                "numeric_id": 17,
                "metric_code": "WIND_SPEED_KMH",
                "display_name": "Velocidad del viento",
                "description": "Velocidad del viento medida en kilometros por hora.",
                "canonical_unit": "km/h",
                "storage_type": "float",
                "scale_factor": 1,
                "physical_min": 0,
                "physical_max": None,
                "default_decimals": 1,
                "default_chart_type": "line",
                "aggregation_strategy": "avg",
                "product_compatibility": "RAIN_GAUGE",
                "client_visibility": True,
                "is_derived": False,
                "calibration_method": None,
                "alert_supported": True,
                "display_order": 170,
                "registry_version": 2,
        },
        {
                "numeric_id": 18,
                "metric_code": "WIND_DIRECTION_DEG",
                "display_name": "Direccion del viento",
                "description": "Direccion meteorologica del viento en grados.",
                "canonical_unit": "degree",
                "storage_type": "float",
                "scale_factor": 1,
                "physical_min": 0,
                "physical_max": 360,
                "default_decimals": 0,
                "default_chart_type": "line",
                "aggregation_strategy": "circular_mean",
                "product_compatibility": "RAIN_GAUGE",
                "client_visibility": True,
                "is_derived": False,
                "calibration_method": None,
                "alert_supported": False,
                "display_order": 180,
                "registry_version": 2,
        },
    ]
    metric_codes = tuple(row["metric_code"] for row in rows)
    existing_codes = set(
        op.get_bind().execute(
            sa.select(definitions.c.metric_code).where(definitions.c.metric_code.in_(metric_codes))
        ).scalars()
    )
    missing_rows = [row for row in rows if row["metric_code"] not in existing_codes]
    if missing_rows:
        op.bulk_insert(definitions, missing_rows)

    op.execute(
        definitions.update()
        .where(definitions.c.metric_code == "RAIN_DELTA_MM")
        .values(aggregation_strategy="sum")
    )
    op.execute(
        definitions.update()
        .where(definitions.c.metric_code == "WIND_SPEED_KMH")
        .values(aggregation_strategy="avg")
    )
    op.execute(
        definitions.update()
        .where(definitions.c.metric_code == "WIND_DIRECTION_DEG")
        .values(aggregation_strategy="circular_mean")
    )

    op.execute(
        definitions.update()
        .where(definitions.c.metric_code == "AMBIENT_TEMPERATURE_C")
        .values(product_compatibility="SILO_SENSOR,CAMPO_SENSOR,RAIN_GAUGE", aggregation_strategy="avg")
    )
    op.execute(
        definitions.update()
        .where(definitions.c.metric_code == "AMBIENT_RELATIVE_HUMIDITY_PCT")
        .values(product_compatibility="SILO_SENSOR,CAMPO_SENSOR,RAIN_GAUGE", aggregation_strategy="avg")
    )
    op.execute(
        definitions.update()
        .where(definitions.c.metric_code == "BATTERY_PERCENT")
        .values(product_compatibility="SILO_SENSOR,CAMPO_SENSOR,RAIN_GAUGE,GATEWAY", aggregation_strategy="last")
    )
    op.execute(definitions.update().values(registry_version=2))


def downgrade() -> None:
    definitions = sa.table(
        "metric_definitions",
        sa.column("metric_code", sa.String()),
        sa.column("product_compatibility", sa.String()),
        sa.column("registry_version", sa.Integer()),
    )
    op.execute(
        definitions.delete().where(
            definitions.c.metric_code.in_(("RAIN_DELTA_MM", "WIND_SPEED_KMH", "WIND_DIRECTION_DEG"))
        )
    )
    op.execute(
        definitions.update()
        .where(definitions.c.metric_code == "AMBIENT_TEMPERATURE_C")
        .values(product_compatibility="SILO_SENSOR,CAMPO_SENSOR", registry_version=1)
    )
    op.execute(
        definitions.update()
        .where(definitions.c.metric_code == "AMBIENT_RELATIVE_HUMIDITY_PCT")
        .values(product_compatibility="SILO_SENSOR,CAMPO_SENSOR", registry_version=1)
    )
    op.execute(
        definitions.update()
        .where(definitions.c.metric_code == "BATTERY_PERCENT")
        .values(product_compatibility="SILO_SENSOR,CAMPO_SENSOR,GATEWAY", registry_version=1)
    )
    op.execute(definitions.update().values(registry_version=1))

    with op.batch_alter_table("metric_definitions") as batch:
        batch.drop_column("aggregation_strategy")
    with op.batch_alter_table("devices") as batch:
        batch.drop_column("longitude")
        batch.drop_column("latitude")
    with op.batch_alter_table("storage_units") as batch:
        batch.drop_column("boundary_geojson")
    with op.batch_alter_table("sites") as batch:
        batch.drop_column("boundary_geojson")

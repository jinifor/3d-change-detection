"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-25
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "project",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("crs_epsg", sa.Integer(), nullable=True),
        sa.Column("origin_x", sa.Float(), nullable=True),
        sa.Column("origin_y", sa.Float(), nullable=True),
        sa.Column("registration_rmse", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "job",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("registration_matrix", sa.JSON(), nullable=True),
        sa.Column("registration_decision", sa.String(length=16), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_job_project_id"), "job", ["project_id"], unique=False)

    op.create_table(
        "tile",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("tile_key", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("bbox", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tile_project_id"), "tile", ["project_id"], unique=False)

    op.create_table(
        "candidate",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("tile_id", sa.String(length=36), nullable=True),
        sa.Column("geometry", geoalchemy2.Geometry(geometry_type="POLYGON"), nullable=False),
        sa.Column("centroid", geoalchemy2.Geometry(geometry_type="POINT"), nullable=False),
        sa.Column("bbox", sa.JSON(), nullable=False),
        sa.Column("area", sa.Float(), nullable=False),
        sa.Column("point_count", sa.Integer(), nullable=False),
        sa.Column("distance_mean", sa.Float(), nullable=False),
        sa.Column("distance_max", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=True),
        sa.Column("height", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        sa.ForeignKeyConstraint(["tile_id"], ["tile.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_candidate_project_id"), "candidate", ["project_id"], unique=False)
    op.create_index(op.f("ix_candidate_tile_id"), "candidate", ["tile_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_candidate_tile_id"), table_name="candidate")
    op.drop_index(op.f("ix_candidate_project_id"), table_name="candidate")
    op.drop_table("candidate")
    op.drop_index(op.f("ix_tile_project_id"), table_name="tile")
    op.drop_table("tile")
    op.drop_index(op.f("ix_job_project_id"), table_name="job")
    op.drop_table("job")
    op.drop_table("project")

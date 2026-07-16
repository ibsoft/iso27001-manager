"""Add picture and barcode columns to asset

Revision ID: 0001_add_picture_barcode
Revises: None
Create Date: 2026-07-16 16:09:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "0001_add_picture_barcode"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("asset", sa.Column("picture", sa.String(256), nullable=True))
    op.add_column("asset", sa.Column("barcode", sa.String(256), nullable=True))


def downgrade():
    op.drop_column("asset", "picture")
    op.drop_column("asset", "barcode")

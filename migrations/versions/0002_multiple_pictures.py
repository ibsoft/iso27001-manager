"""Add support for multiple asset pictures (JSON array in picture column)

Revision ID: 0002_multiple_pictures
Revises: 0001_add_picture_barcode
Create Date: 2026-07-20 16:00:00.000000

"""
import json
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = "0002_multiple_pictures"
down_revision = "0001_add_picture_barcode"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("asset", "picture", type_=sa.Text(), existing_type=sa.String(256))
    conn = op.get_bind()
    rows = conn.execute(
        text("SELECT id, picture FROM asset WHERE picture IS NOT NULL AND picture != ''")
    ).fetchall()
    for row in rows:
        val = row[1]
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                continue
        except (json.JSONDecodeError, TypeError):
            pass
        conn.execute(
            text("UPDATE asset SET picture = :val WHERE id = :id"),
            {"val": json.dumps([val]), "id": row[0]},
        )
    conn.execute(
        text("UPDATE asset SET picture = '[]' WHERE picture IS NULL OR picture = ''")
    )


def downgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == "postgresql":
        conn.execute(
            text(
                "UPDATE asset SET picture = "
                "CASE WHEN picture IS NOT NULL AND picture != '[]' "
                "THEN picture::json->>0 "
                "ELSE NULL END"
            )
        )
    else:
        conn.execute(
            text(
                "UPDATE asset SET picture = "
                "CASE WHEN picture IS NOT NULL AND picture != '[]' "
                "THEN json_extract(picture, '$[0]') "
                "ELSE NULL END"
            )
        )
    op.alter_column("asset", "picture", type_=sa.String(256), existing_type=sa.Text())

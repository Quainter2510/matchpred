"""multi-room: rooms + room_members, room_id on predictions/special_predictions

Migrates the single existing tournament into the first room and re-scopes all
predictions, special predictions and members to it.

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- new tables ---
    op.create_table(
        "rooms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("first_match_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
    )
    op.create_index("ix_rooms_name", "rooms", ["name"])

    op.create_table(
        "room_members",
        sa.Column("room_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rooms.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("room_role", sa.String(20), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("total_points", sa.Integer(), server_default="0"),
        sa.Column("exact_scores_count", sa.Integer(), server_default="0"),
        sa.Column("participation_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        "ix_room_members_leaderboard",
        "room_members",
        ["room_id", "total_points", "exact_scores_count"],
    )

    # --- add room_id (nullable for backfill) ---
    op.add_column("predictions", sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("special_predictions", sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=True))

    # --- migrate the single existing tournament into the first room ---
    op.execute(
        """
        INSERT INTO rooms (id, name, password_hash, first_match_at, created_by, created_at, is_active)
        SELECT t.id, t.name, t.password_hash, t.first_match_at,
               (SELECT id FROM users WHERE system_role = 'superadmin' ORDER BY created_at LIMIT 1),
               now(), t.is_active
        FROM tournament t
        """
    )
    op.execute(
        """
        INSERT INTO room_members (room_id, user_id, room_role, joined_at, total_points, exact_scores_count, participation_confirmed)
        SELECT (SELECT id FROM rooms ORDER BY created_at LIMIT 1),
               tm.user_id, tm.tournament_role, tm.joined_at, tm.total_points, tm.exact_scores_count, tm.participation_confirmed
        FROM tournament_members tm
        WHERE EXISTS (SELECT 1 FROM rooms)
        """
    )
    op.execute("UPDATE predictions SET room_id = (SELECT id FROM rooms ORDER BY created_at LIMIT 1) WHERE room_id IS NULL")
    op.execute("UPDATE special_predictions SET room_id = (SELECT id FROM rooms ORDER BY created_at LIMIT 1) WHERE room_id IS NULL")

    # Drop any prediction/special rows that could not be scoped (no room existed).
    op.execute("DELETE FROM predictions WHERE room_id IS NULL")
    op.execute("DELETE FROM special_predictions WHERE room_id IS NULL")

    # --- swap constraints/indexes on predictions ---
    op.drop_constraint("uq_user_match", "predictions", type_="unique")
    op.drop_index("ix_predictions_match_id", table_name="predictions")
    op.drop_index("ix_predictions_user_id", table_name="predictions")
    op.alter_column("predictions", "room_id", nullable=False)
    op.create_foreign_key(
        "fk_predictions_room", "predictions", "rooms", ["room_id"], ["id"], ondelete="CASCADE"
    )
    op.create_unique_constraint("uq_room_user_match", "predictions", ["room_id", "user_id", "match_id"])
    op.create_index("ix_predictions_room_match", "predictions", ["room_id", "match_id"])
    op.create_index("ix_predictions_room_user", "predictions", ["room_id", "user_id"])

    # --- swap constraints on special_predictions ---
    op.execute("ALTER TABLE special_predictions DROP CONSTRAINT IF EXISTS special_predictions_user_id_key")
    op.alter_column("special_predictions", "room_id", nullable=False)
    op.create_foreign_key(
        "fk_special_room", "special_predictions", "rooms", ["room_id"], ["id"], ondelete="CASCADE"
    )
    op.create_unique_constraint("uq_room_user_special", "special_predictions", ["room_id", "user_id"])

    # --- drop legacy single-tournament tables ---
    op.drop_table("tournament_members")
    op.drop_table("tournament")


def downgrade() -> None:
    # One-way migration (single tournament cannot be reconstructed from many rooms).
    raise NotImplementedError("Downgrade from multi-room is not supported.")

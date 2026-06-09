"""initial schema — all 8 tables

Revision ID: 0001
Revises:
Create Date: 2026-06-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("nickname", sa.String(24), nullable=False, unique=True),
        sa.Column("avatar_url", sa.String(), nullable=True),
        sa.Column("system_role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
    )

    op.create_table(
        "oauth_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("provider_user_id", sa.String(100), nullable=False),
        sa.Column("access_token_enc", sa.String(), nullable=True),
        sa.Column("refresh_token_enc", sa.String(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_provider_user"),
    )

    op.create_table(
        "tournament",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("first_match_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
    )

    op.create_table(
        "tournament_members",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tournament_role", sa.String(20), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("total_points", sa.Integer(), server_default="0"),
        sa.Column("exact_scores_count", sa.Integer(), server_default="0"),
    )
    op.create_index("ix_members_leaderboard", "tournament_members", ["total_points", "exact_scores_count"])

    op.create_table(
        "matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("api_football_id", sa.Integer(), nullable=True, unique=True),
        sa.Column("match_date", sa.Date(), nullable=False),
        sa.Column("kickoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stage", sa.String(40), nullable=False),
        sa.Column("home_team", sa.String(100), nullable=False),
        sa.Column("away_team", sa.String(100), nullable=False),
        sa.Column("home_score_ft", sa.Integer(), nullable=True),
        sa.Column("away_score_ft", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), server_default="scheduled"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_matches_match_date", "matches", ["match_date"])
    op.create_index("ix_matches_kickoff_at", "matches", ["kickoff_at"])

    op.create_table(
        "predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("match_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("predicted_home", sa.SmallInteger(), nullable=False),
        sa.Column("predicted_away", sa.SmallInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("points_awarded", sa.SmallInteger(), nullable=True),
        sa.Column("is_exact", sa.Boolean(), nullable=True),
        sa.UniqueConstraint("user_id", "match_id", name="uq_user_match"),
    )
    op.create_index("ix_predictions_match_id", "predictions", ["match_id"])
    op.create_index("ix_predictions_user_id", "predictions", ["user_id"])

    op.create_table(
        "special_predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("champion_team", sa.String(100), nullable=True),
        sa.Column("top_scorer_name", sa.String(150), nullable=True),
        sa.Column("top_scorer_api_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("champion_points", sa.SmallInteger(), nullable=True),
        sa.Column("scorer_points", sa.SmallInteger(), nullable=True),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("actor_nickname", sa.String(24), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_audit_created_at", "audit_log", ["created_at"])
    op.create_index("ix_audit_event_type", "audit_log", ["event_type"])
    op.create_index("ix_audit_actor_id", "audit_log", ["actor_id"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("special_predictions")
    op.drop_table("predictions")
    op.drop_table("matches")
    op.drop_table("tournament_members")
    op.drop_table("tournament")
    op.drop_table("oauth_accounts")
    op.drop_table("users")

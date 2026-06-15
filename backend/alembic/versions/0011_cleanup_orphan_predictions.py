"""cleanup predictions of users no longer in the room

Removing a member used to leave their predictions/special predictions behind
(no DB cascade on member removal). Those orphans still surfaced in lists. This
one-off cleanup deletes prediction rows whose (room_id, user_id) is not an active
room member. Going forward `remove_member` deletes them explicitly.

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-15
"""
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM predictions p
        WHERE NOT EXISTS (
            SELECT 1 FROM room_members rm
            WHERE rm.room_id = p.room_id AND rm.user_id = p.user_id
        )
        """
    )
    op.execute(
        """
        DELETE FROM special_predictions sp
        WHERE NOT EXISTS (
            SELECT 1 FROM room_members rm
            WHERE rm.room_id = sp.room_id AND rm.user_id = sp.user_id
        )
        """
    )


def downgrade() -> None:
    # Удалённые осиротевшие прогнозы восстановить нельзя — no-op.
    pass

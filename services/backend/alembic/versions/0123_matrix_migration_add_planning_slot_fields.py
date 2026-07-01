"""Matrix Rendering Migration: Add fields to PlanningSlot and Invitation

This migration adds the following fields to support the matrix rendering migration
(Task Group 1.1) where matrix uses only PlanningSlot/EventInstance instead of Event:

PlanningSlot:
- title: str | None - Title for the slot (used when no EventInstance exists)
- approval_status: EventApprovalStatus | None - Approval status for planning workflow
- invitation_source_congregation_id: uuid.UUID | None - Source congregation for invitations
- invitation_source_event_id: uuid.UUID | None - Source event for invitations (legacy)
- applicability: list[uuid.UUID] - List of congregation IDs this slot applies to

CongregationInvitation:
- source_planning_slot_id: uuid.UUID | None - Source PlanningSlot for invitations

Revision ID: 0123_matrix_migration_add_planning_slot_fields
Revises: faecec299731
Create Date: 2025-06-19

"""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0123_matrix_migration_add_planning_slot_fields"
down_revision = "faecec299731"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add new fields to PlanningSlot and CongregationInvitation for matrix migration."""
    # Add fields to planning_slots table
    op.add_column(
        "planning_slots",
        sa.Column("title", sa.String(length=500), nullable=True),
    )
    
    # Create the event_approval_status enum if it doesn't exist
    # Check if the enum type exists
    enum_name = "event_approval_status"
    
    # For PostgreSQL, we need to check if the enum exists
    # This is a simplified approach - in production, use proper enum handling
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'event_approval_status') THEN
                CREATE TYPE event_approval_status AS ENUM ('PLANNED', 'CONFIRMED');
            END IF;
        END $$;
        """
    )
    
    op.add_column(
        "planning_slots",
        sa.Column("approval_status", sa.Enum("PLANNED", "CONFIRMED", name=enum_name), nullable=True),
    )
    
    op.add_column(
        "planning_slots",
        sa.Column("invitation_source_congregation_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    
    op.add_column(
        "planning_slots",
        sa.Column("invitation_source_event_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    
    op.add_column(
        "planning_slots",
        sa.Column("applicability", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False, server_default="{}"),
    )
    
    # Add foreign key constraints for the new UUID fields
    op.create_foreign_key(
        "fk_planning_slots_inv_src_congregation_id_congregations",
        "planning_slots",
        "congregations",
        ["invitation_source_congregation_id"],
        ["id"],
        ondelete="SET NULL",
    )
    
    op.create_foreign_key(
        "fk_planning_slots_invitation_source_event_id_events",
        "planning_slots",
        "events",
        ["invitation_source_event_id"],
        ["id"],
        ondelete="SET NULL",
    )
    
    # Add field to congregation_invitations table
    op.add_column(
        "congregation_invitations",
        sa.Column("source_planning_slot_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    
    # Add foreign key constraint
    op.create_foreign_key(
        "fk_cong_invitations_src_planning_slot_id_planning_slots",
        "congregation_invitations",
        "planning_slots",
        ["source_planning_slot_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Remove the fields added in upgrade."""
    # Remove foreign key constraints first
    op.drop_constraint(
        "fk_cong_invitations_src_planning_slot_id_planning_slots",
        "congregation_invitations",
        type_="foreignkey",
    )
    
    op.drop_constraint(
        "fk_planning_slots_invitation_source_event_id_events",
        "planning_slots",
        type_="foreignkey",
    )
    
    op.drop_constraint(
        "fk_planning_slots_inv_src_congregation_id_congregations",
        "planning_slots",
        type_="foreignkey",
    )
    
    # Remove columns
    op.drop_column("congregation_invitations", "source_planning_slot_id")
    op.drop_column("planning_slots", "applicability")
    op.drop_column("planning_slots", "invitation_source_event_id")
    op.drop_column("planning_slots", "invitation_source_congregation_id")
    op.drop_column("planning_slots", "approval_status")
    op.drop_column("planning_slots", "title")

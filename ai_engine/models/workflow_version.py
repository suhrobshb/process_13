from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any, TYPE_CHECKING

from sqlmodel import SQLModel, Field, JSON, Relationship

# Use a forward reference for the Workflow model to prevent circular import errors.
# The `if TYPE_CHECKING:` block ensures this import is only used for static type analysis.
if TYPE_CHECKING:
    from .workflow import Workflow


class WorkflowVersion(SQLModel, table=True):
    """
    Represents a specific, immutable snapshot of a workflow's configuration,
    providing comprehensive change tracking and rollback capabilities.

    This model is the foundation for collaboration, auditing, version control,
    and rollback functionalities. Each time a user saves significant changes to a
    workflow, a new WorkflowVersion record is created to capture that state in
    time, providing a complete history of its evolution.

    Change Tracking:
    Is achieved by comparing the `data` JSON blob between two different versions
    of the same workflow. A "diff" can be generated to show exactly what changed
    in the steps, nodes, or triggers.

    Rollback Capability:
    A "rollback" is a non-destructive operation. To roll back to a previous
    version, the application should take the `data` from an older `WorkflowVersion`
    record and use it to create a *new* version. This preserves the full,
    unbroken history of the workflow while reverting its active state.
    """
    id: Optional[int] = Field(default=None, primary_key=True)

    # --- Link to Parent Workflow ---
    workflow_id: int = Field(
        foreign_key="workflow.id",
        index=True,
        description="The ID of the parent Workflow this version belongs to."
    )
    # The back-populating relationship to the Workflow model.
    # This assumes the parent Workflow model has a `versions: List["WorkflowVersion"]` field.
    workflow: "Workflow" = Relationship(back_populates="versions")

    # --- Versioning & Branching Metadata ---
    version_number: int = Field(
        description="A sequential, auto-incrementing version number specific to the parent workflow (e.g., 1, 2, 3)."
    )
    branch_name: str = Field(
        default="main",
        index=True,
        description="The development branch this version belongs to, enabling parallel development strategies (e.g., 'main', 'feature/new-integration')."
    )
    comment: Optional[str] = Field(
        default=None,
        description="A user-provided comment describing the changes in this version, similar to a git commit message."
    )

    # --- Workflow State Snapshot (Core of Change Tracking) ---
    data: Dict[str, Any] = Field(
        sa_column=Field(JSON),
        description="A complete JSON snapshot of the workflow's state (including steps, nodes, edges, and triggers) at the time of versioning. This data is used for diffing and rollbacks."
    )

    # --- Auditing & Collaboration ---
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        description="The timestamp when this version was created."
    )
    created_by: str = Field(
        description="The username or ID of the user or service account that created this version."
    )

    # --- Approval Lifecycle Management ---
    approval_status: str = Field(
        default="draft",
        index=True,
        description="The approval status of this version, facilitating review workflows (e.g., 'draft', 'pending_review', 'approved', 'rejected')."
    )
    approved_by: Optional[str] = Field(
        default=None,
        description="The username or ID of the user who approved or rejected this version."
    )
    approval_timestamp: Optional[datetime] = Field(
        default=None,
        description="The timestamp when the approval or rejection occurred."
    )
    approval_notes: Optional[str] = Field(
        default=None,
        description="Optional notes or comments provided by the approver during the review process."
    )

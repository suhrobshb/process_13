from datetime import datetime
from typing import Optional, Dict
from sqlmodel import SQLModel, Field, JSON, Relationship

class Execution(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    workflow_id: int = Field(foreign_key="workflow.id")
    status: str = "pending"  # pending, running, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[str] = None
    result: Optional[Dict] = Field(default={}, sa_type=JSON)
    extra_metadata: Dict = Field(default={}, sa_type=JSON) 
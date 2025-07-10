from datetime import datetime
from typing import Optional, Dict
from sqlmodel import SQLModel, Field, JSON

class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    status: str = Field(default="uploaded")  # uploaded → processing → completed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    workflow_id: Optional[int] = Field(default=None, foreign_key="workflow.id")
    extra_metadata: Dict = Field(default={}, sa_type=JSON)  # will store clusters, intents, etc.
    user_id: Optional[int] = None 
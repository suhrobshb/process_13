from datetime import datetime
from typing import Optional, List, Dict
from sqlmodel import SQLModel, Field, JSON, Relationship

class Workflow(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    status: str = "draft"  # draft, active, archived
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    steps: List[Dict] = Field(default=[], sa_type=JSON)
    triggers: List[Dict] = Field(default=[], sa_type=JSON)
    approvals: List[Dict] = Field(default=[], sa_type=JSON)
    extra_metadata: Dict = Field(default={}, sa_type=JSON) 
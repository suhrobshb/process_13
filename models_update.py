#!/usr/bin/env python3
"""
Database Models Update
======================

This file contains additional database models and updates needed for the
enhanced functionality.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, JSON, Column, DateTime
from sqlalchemy import func

# =============================================================================
# Enhanced Models
# =============================================================================

class RecordingSession(SQLModel, table=True):
    """Recording session for capturing user workflows"""
    __tablename__ = "recording_sessions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(unique=True, index=True)
    workflow_name: str
    status: str = Field(default="recording")  # recording, stopped, processing, completed
    started_at: Optional[datetime] = Field(default_factory=datetime.now)
    stopped_at: Optional[datetime] = None
    session_metadata: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    
    # Relationships
    events: List["RecordingEvent"] = Relationship(back_populates="session")

class RecordingEvent(SQLModel, table=True):
    """Individual events captured during recording"""
    __tablename__ = "recording_events"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="recording_sessions.session_id")
    event_type: str  # click, type, window_change, hotkey, etc.
    timestamp: datetime = Field(default_factory=datetime.now)
    screen_position: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    element_info: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    event_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    
    # Relationships
    session: Optional[RecordingSession] = Relationship(back_populates="events")

class WorkflowAnalytics(SQLModel, table=True):
    """Analytics data for workflows"""
    __tablename__ = "workflow_analytics"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    workflow_id: int = Field(foreign_key="workflow.id")
    metric_name: str
    metric_value: float
    recorded_at: datetime = Field(default_factory=datetime.now)
    metric_metadata: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

class SystemMetrics(SQLModel, table=True):
    """System performance metrics"""
    __tablename__ = "system_metrics"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    metric_name: str
    metric_value: float
    metric_unit: str
    recorded_at: datetime = Field(default_factory=datetime.now)
    component: str  # api, database, ai_engine, etc.

class UserSession(SQLModel, table=True):
    """User session tracking"""
    __tablename__ = "user_sessions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(unique=True, index=True)
    user_id: Optional[str] = Field(default="default_user")
    started_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(default=True)
    session_info: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

class NLPInteraction(SQLModel, table=True):
    """NLP command interactions"""
    __tablename__ = "nlp_interactions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_command: str
    parsed_intent: str
    confidence_score: float
    created_workflow: Optional[bool] = Field(default=False)
    workflow_id: Optional[int] = Field(default=None, foreign_key="workflow.id")
    created_at: datetime = Field(default_factory=datetime.now)
    execution_successful: Optional[bool] = None

class CollaborationSession(SQLModel, table=True):
    """Collaboration sessions for workflow editing"""
    __tablename__ = "collaboration_sessions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(unique=True, index=True)
    workflow_id: int = Field(foreign_key="workflow.id")
    created_by: str
    created_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(default=True)
    participants: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))

class Notification(SQLModel, table=True):
    """System notifications"""
    __tablename__ = "notifications"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(default="default_user")
    title: str
    message: str
    notification_type: str  # info, warning, error, success
    is_read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)
    read_at: Optional[datetime] = None
    notification_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

class GameAchievement(SQLModel, table=True):
    """Gamification achievements"""
    __tablename__ = "game_achievements"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(default="default_user")
    achievement_type: str  # workflow_created, hours_saved, accuracy_improved, etc.
    achievement_name: str
    description: str
    points_earned: int
    earned_at: datetime = Field(default_factory=datetime.now)
    achievement_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

class WorkflowTemplate(SQLModel, table=True):
    """Predefined workflow templates"""
    __tablename__ = "workflow_templates"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str
    category: str  # finance, hr, marketing, etc.
    template_data: Dict[str, Any] = Field(sa_column=Column(JSON))
    usage_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    is_active: bool = Field(default=True)

class APIUsageLog(SQLModel, table=True):
    """API usage logging"""
    __tablename__ = "api_usage_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    endpoint: str
    method: str  # GET, POST, PUT, DELETE
    user_id: str = Field(default="default_user")
    response_status: int
    response_time_ms: int
    request_timestamp: datetime = Field(default_factory=datetime.now)
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None

class WorkflowVersion(SQLModel, table=True):
    """Workflow version control"""
    __tablename__ = "workflow_versions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    workflow_id: int = Field(foreign_key="workflow.id")
    version_number: int
    workflow_data: Dict[str, Any] = Field(sa_column=Column(JSON))
    created_by: str = Field(default="default_user")
    created_at: datetime = Field(default_factory=datetime.now)
    change_description: Optional[str] = None
    is_active: bool = Field(default=False)

# =============================================================================
# Enhanced Existing Models (Extensions)
# =============================================================================

class WorkflowExtension(SQLModel, table=True):
    """Extended workflow properties"""
    __tablename__ = "workflow_extensions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    workflow_id: int = Field(foreign_key="workflow.id", unique=True)
    
    # Performance metrics
    average_execution_time: Optional[float] = None
    success_rate: Optional[float] = None
    last_optimization: Optional[datetime] = None
    
    # Collaboration
    is_collaborative: bool = Field(default=False)
    shared_with: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    
    # Gamification
    total_runs: int = Field(default=0)
    total_time_saved: int = Field(default=0)  # in seconds
    efficiency_score: Optional[float] = None
    
    # Additional data
    tags: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    priority: str = Field(default="medium")  # low, medium, high, critical
    business_value: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

class TaskExtension(SQLModel, table=True):
    """Extended task properties"""
    __tablename__ = "task_extensions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="task.id", unique=True)
    
    # Recording data
    recording_session_id: Optional[str] = Field(default=None, foreign_key="recording_sessions.session_id")
    
    # AI Analysis
    complexity_score: Optional[float] = None
    automation_confidence: Optional[float] = None
    estimated_time_savings: Optional[int] = None  # in seconds
    
    # Categorization
    task_category: Optional[str] = None
    business_process: Optional[str] = None
    
    # Additional info
    source: str = Field(default="manual")  # manual, recorded, imported
    validation_status: str = Field(default="pending")  # pending, validated, rejected
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

class ExecutionExtension(SQLModel, table=True):
    """Extended execution properties"""
    __tablename__ = "execution_extensions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    execution_id: int = Field(foreign_key="execution.id", unique=True)
    
    # Performance metrics
    cpu_usage_peak: Optional[float] = None
    memory_usage_peak: Optional[float] = None
    network_calls: Optional[int] = None
    
    # Error tracking
    error_count: int = Field(default=0)
    warning_count: int = Field(default=0)
    retry_count: int = Field(default=0)
    
    # Context
    trigger_source: str = Field(default="manual")  # manual, scheduled, webhook, nlp
    execution_context: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    
    # Quality metrics
    accuracy_score: Optional[float] = None
    user_satisfaction: Optional[int] = None  # 1-5 rating
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

# =============================================================================
# Export all models
# =============================================================================

ENHANCED_MODELS = [
    RecordingSession,
    RecordingEvent,
    WorkflowAnalytics,
    SystemMetrics,
    UserSession,
    NLPInteraction,
    CollaborationSession,
    Notification,
    GameAchievement,
    WorkflowTemplate,
    APIUsageLog,
    WorkflowVersion,
    WorkflowExtension,
    TaskExtension,
    ExecutionExtension
]

__all__ = [
    "RecordingSession",
    "RecordingEvent", 
    "WorkflowAnalytics",
    "SystemMetrics",
    "UserSession",
    "NLPInteraction",
    "CollaborationSession",
    "Notification",
    "GameAchievement",
    "WorkflowTemplate",
    "APIUsageLog",
    "WorkflowVersion",
    "WorkflowExtension",
    "TaskExtension",
    "ExecutionExtension",
    "ENHANCED_MODELS"
]
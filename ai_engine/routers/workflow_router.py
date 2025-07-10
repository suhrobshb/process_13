from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlmodel import Session, select
from ..database import get_session
from ..models.workflow import Workflow
from ..tasks import execute_workflow

router = APIRouter(prefix="/workflows", tags=["workflows"])

@router.post("/", response_model=Workflow)
def create_workflow(workflow: Workflow, session: Session = Depends(get_session)):
    session.add(workflow); session.commit(); session.refresh(workflow)
    return workflow

@router.get("/", response_model=List[Workflow])
def list_workflows(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
    """
    Return a paginated list of workflows using SQLModel's modern `select`
    syntax instead of the legacy `session.query(...)` API (which produces
    SAWarning messages with SQLAlchemy 2.x).
    """
    statement = select(Workflow).offset(skip).limit(limit)
    return session.exec(statement).all()

@router.get("/{workflow_id}", response_model=Workflow)
def get_workflow(workflow_id: int, session: Session = Depends(get_session)):
    wf = session.get(Workflow, workflow_id)
    if not wf: raise HTTPException(404,"Workflow not found")
    return wf

@router.put("/{workflow_id}", response_model=Workflow)
def update_workflow(workflow_id: int, data: Workflow, session: Session = Depends(get_session)):
    wf = session.get(Workflow, workflow_id)
    if not wf: raise HTTPException(404,"Workflow not found")
    # SQLModel ≥ 0.0.14 deprecates `.dict()` in favour of `.model_dump()`
    # Use the new API to silence deprecation warnings.
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(wf, k, v)
    session.add(wf); session.commit(); session.refresh(wf)
    return wf

@router.delete("/{workflow_id}")
def delete_workflow(workflow_id: int, session: Session = Depends(get_session)):
    wf = session.get(Workflow, workflow_id)
    if not wf: raise HTTPException(404,"Workflow not found")
    session.delete(wf); session.commit()
    return {"status":"deleted"}

@router.post("/{workflow_id}/activate")
def activate_workflow(workflow_id: int, session: Session = Depends(get_session)):
    wf = session.get(Workflow, workflow_id)
    if not wf: raise HTTPException(404,"Workflow not found")
    wf.status="active"; session.add(wf); session.commit()
    return {"status":"activated"}

@router.post("/{workflow_id}/deactivate")
def deactivate_workflow(workflow_id: int, session: Session = Depends(get_session)):
    wf = session.get(Workflow, workflow_id)
    if not wf: raise HTTPException(404,"Workflow not found")
    wf.status="draft"; session.add(wf); session.commit()
    return {"status":"deactivated"}

@router.post("/{workflow_id}/clone", response_model=Workflow)
def clone_workflow(workflow_id: int, session: Session = Depends(get_session)):
    orig = session.get(Workflow, workflow_id)
    if not orig: raise HTTPException(404,"Workflow not found")
    clone = Workflow(
        name=f"{orig.name} (copy)",
        description=orig.description,
        status="draft",
        created_by=orig.created_by,
        steps=orig.steps,
        triggers=orig.triggers,
        approvals=orig.approvals,
        extra_metadata=orig.extra_metadata,
    )
    session.add(clone); session.commit(); session.refresh(clone)
    return clone

@router.post("/{workflow_id}/trigger")
def manual_trigger(workflow_id: int, session: Session = Depends(get_session)):
    wf = session.get(Workflow, workflow_id)
    if not wf: raise HTTPException(404,"Workflow not found")
    if wf.status!="active": raise HTTPException(400,"Cannot trigger inactive")
    execute_workflow.delay(workflow_id)
    return {"status":"triggered"} 
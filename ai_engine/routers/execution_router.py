import time
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from sqlmodel import Session, select
from ..database import get_session
from ..models.execution import Execution
from ..tasks import execute_workflow
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/executions", tags=["executions"])

@router.post("/", response_model=Execution)
def create_execution(execution: Execution, session: Session = Depends(get_session)):
    session.add(execution); session.commit(); session.refresh(execution)
    return execution

@router.get("/", response_model=List[Execution])
def list_executions(skip: int=0, limit: int=100,
                    status: Optional[str]=None,
                    workflow_id: Optional[int]=None,
                    session: Session=Depends(get_session)):
    q = select(Execution)
    if status: q = q.where(Execution.status==status)
    if workflow_id: q = q.where(Execution.workflow_id==workflow_id)
    return session.exec(q.offset(skip).limit(limit)).all()

@router.get("/{exec_id}", response_model=Execution)
def get_execution(exec_id: int, session: Session = Depends(get_session)):
    ex = session.get(Execution, exec_id)
    if not ex: raise HTTPException(404,"Execution not found")
    return ex

@router.put("/{exec_id}", response_model=Execution)
def update_execution(exec_id: int, data: Execution, session: Session = Depends(get_session)):
    ex = session.get(Execution, exec_id)
    if not ex: raise HTTPException(404,"Execution not found")
    for k,v in data.dict(exclude_unset=True).items():
        setattr(ex, k, v)
    session.add(ex); session.commit(); session.refresh(ex)
    return ex

@router.delete("/{exec_id}")
def delete_execution(exec_id: int, session: Session = Depends(get_session)):
    ex = session.get(Execution, exec_id)
    if not ex: raise HTTPException(404,"Execution not found")
    session.delete(ex); session.commit()
    return {"status":"deleted"}

@router.post("/{exec_id}/retry")
def retry_execution(exec_id: int, session: Session = Depends(get_session)):
    ex = session.get(Execution, exec_id)
    if not ex: raise HTTPException(404,"Execution not found")
    execute_workflow.delay(ex.workflow_id)
    return {"status":"retry enqueued"}

@router.post("/{exec_id}/rollback")
def rollback_execution(exec_id: int, session: Session = Depends(get_session)):
    ex = session.get(Execution, exec_id)
    if not ex: raise HTTPException(404,"Execution not found")
    ex.status="pending"; session.add(ex); session.commit()
    return {"status":"rolled back"}

@router.get("/{exec_id}/stream")
def stream_execution(exec_id: int):
    def event_generator():
        while True:
            from ..database import get_session as _get_session
            with _get_session() as s:
                ex = s.get(Execution, exec_id)
                yield {
                    "event": "status",
                    "id": exec_id,
                    "status": ex.status,
                    "updated_at": ex.updated_at.isoformat()
                }
                if ex.status in ("completed","failed"):
                    break
            time.sleep(1)
    return EventSourceResponse(event_generator()) 
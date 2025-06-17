import os, shutil, json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import List
from sqlmodel import Session, select
from ..database import get_session
from ..models.task import Task
from ..tasks import process_task
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/upload", response_model=Task)
async def upload_recording(
    file: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    user_id = 1  # replace with auth
    user_dir = f"storage/users/{user_id}/recordings"
    os.makedirs(user_dir, exist_ok=True)
    dest = os.path.join(user_dir, file.filename)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    task = Task(filename=file.filename, user_id=user_id)
    session.add(task); session.commit(); session.refresh(task)
    process_task.delay(task.id)
    return task

@router.get("/", response_model=List[Task])
def list_tasks(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
    user_id = 1
    tasks = session.exec(
        select(Task).where(Task.user_id==user_id).offset(skip).limit(limit)
    ).all()
    return tasks

@router.get("/{task_id}", response_model=Task)
def get_task(task_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task: raise HTTPException(404, "Task not found")
    return task

@router.put("/{task_id}", response_model=Task)
def update_task(task_id: int, data: Task, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task: raise HTTPException(404, "Task not found")
    for k,v in data.dict(exclude_unset=True).items():
        setattr(task, k, v)
    session.add(task); session.commit(); session.refresh(task)
    return task

@router.delete("/{task_id}")
def delete_task(task_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task: raise HTTPException(404, "Task not found")
    path = f"storage/users/{task.user_id}/recordings/{task.filename}"
    if os.path.exists(path): os.remove(path)
    session.delete(task); session.commit()
    return {"status":"deleted"}

@router.get("/{task_id}/logs")
def get_task_logs(task_id: int):
    path = f"storage/users/1/recordings/{task_id}/events.json"
    if not os.path.exists(path): raise HTTPException(404,"Logs not found")
    return EventSourceResponse(json.load(open(path)))

@router.get("/{task_id}/clusters")
def get_task_clusters(task_id: int):
    path = f"storage/users/1/recordings/{task_id}_clusters.json"
    if not os.path.exists(path): raise HTTPException(404,"Clusters not found")
    return json.load(open(path))

@router.post("/upload_chunk")
async def upload_chunk(
    task_id: int,
    chunk_index: int,
    total_chunks: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    """
    Receive file chunks and assemble when done.
    """
    user_id = 1  # replace with auth
    chunk_dir = f"storage/users/{user_id}/recordings/{task_id}/chunks"
    os.makedirs(chunk_dir, exist_ok=True)
    chunk_path = os.path.join(chunk_dir, f"{chunk_index}.chunk")
    with open(chunk_path, "wb") as f:
        f.write(await file.read())

    if chunk_index == total_chunks - 1:
        # assemble
        final_dir = f"storage/users/{user_id}/recordings"
        zip_path = os.path.join(final_dir, f"{task_id}.zip")
        with open(zip_path, "wb") as wf:
            for i in range(total_chunks):
                part = os.path.join(chunk_dir, f"{i}.chunk")
                with open(part, "rb") as pf:
                    wf.write(pf.read())
        # cleanup
        import shutil
        shutil.rmtree(chunk_dir)
        # record in DB & enqueue
        task = session.get(Task, task_id)
        if not task:
            raise HTTPException(404, "Task not found")
        task.filename = f"{task_id}.zip"
        session.add(task)
        session.commit()
        process_task.delay(task.id)
        return {"status":"assembled","task_id":task.id}
    return {"status":"chunk_received","index":chunk_index} 
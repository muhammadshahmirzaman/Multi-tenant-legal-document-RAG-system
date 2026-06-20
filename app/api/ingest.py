from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from uuid import uuid4
import os
from app.core.auth import get_current_tenant
from app.workers.ingest_task import ingest_pdf
from celery.result import AsyncResult
from app.core.config import settings

router = APIRouter(prefix="/ingest")

UPLOAD_DIR = ".tmp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/")
async def ingest(file: UploadFile = File(...), tenant_id: str = Depends(get_current_tenant)):
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Only PDF uploads supported")
    task_id = str(uuid4())
    tmp_path = os.path.join(UPLOAD_DIR, f"{task_id}_{file.filename}")
    with open(tmp_path, "wb") as f:
        content = await file.read()
        f.write(content)
    # Push Celery task
    celery_task = ingest_pdf.apply_async(args=[tmp_path, tenant_id, file.filename])
    return {"task_id": celery_task.id, "status": "queued"}


@router.get("/status/{task_id}")
async def status(task_id: str):
    res = AsyncResult(task_id, app=None)
    # AsyncResult requires an app; relying on default celery backend configured
    return {"task_id": task_id, "status": res.status, "result": res.result}

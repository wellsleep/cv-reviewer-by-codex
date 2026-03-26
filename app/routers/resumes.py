from pathlib import Path
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.models.api import ApiResponse
from app.services.resume_service import resume_service

router = APIRouter(tags=["resumes"])


@router.post("/resumes/upload", response_model=ApiResponse)
async def upload_resumes(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="no files uploaded")
    items = await resume_service.save_uploads(files)
    return ApiResponse(message="uploaded", data=items)


@router.get("/resumes/{resume_id}", response_model=ApiResponse)
def get_resume(resume_id: int):
    return ApiResponse(data=resume_service.get_resume_detail(resume_id))


@router.post("/resumes/{resume_id}/retry", response_model=ApiResponse)
def retry_resume(resume_id: int):
    resume_service.retry_resume(resume_id)
    return ApiResponse(message="retry started", data=True)


@router.post("/resumes/retry-all", response_model=ApiResponse)
def retry_all_resumes():
    retried_ids = resume_service.retry_all_resumes()
    return ApiResponse(message="all resumes retried", data={"resumeIds": retried_ids})


@router.get("/resumes/{resume_id}/file", include_in_schema=False)
def get_resume_file(resume_id: int):
    resume = resume_service.get_resume_detail(resume_id)
    file_path = Path(resume["filePath"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="resume file not found")
    return FileResponse(path=file_path, filename=resume["fileName"])

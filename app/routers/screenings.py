from fastapi import APIRouter

from app.models.api import ApiResponse, ScreeningReviewRequest, ScreeningRunRequest
from app.services.screening_service import screening_service

router = APIRouter(tags=["screenings"])


@router.post("/screenings/run", response_model=ApiResponse)
def run_screenings(payload: ScreeningRunRequest):
    task = screening_service.run(payload.resumeIds)
    return ApiResponse(message="screening started", data=task)


@router.post("/screenings/rerun-all", response_model=ApiResponse)
def rerun_all_screenings():
    task = screening_service.rerun_all()
    return ApiResponse(message="screening started", data=task)


@router.get("/screenings/tasks/{task_id}", response_model=ApiResponse)
def get_screening_task(task_id: str):
    return ApiResponse(data=screening_service.get_task(task_id))


@router.get("/screenings/results", response_model=ApiResponse)
def list_screening_results(
    page: int = 1,
    pageSize: int = 10,
    recommendation: str = None,
    keyword: str = None,
    sortBy: str = "createdAt",
    sortOrder: str = "desc",
):
    return ApiResponse(
        data=screening_service.list_results(
            page=page,
            page_size=pageSize,
            recommendation=recommendation,
            keyword=keyword,
            sort_by=sortBy,
            sort_order=sortOrder,
        )
    )


@router.get("/screenings/results/{screening_id}", response_model=ApiResponse)
def get_screening_result(screening_id: int):
    return ApiResponse(data=screening_service.get_result_detail(screening_id))


@router.post("/screenings/results/{screening_id}/review", response_model=ApiResponse)
def review_screening_result(screening_id: int, payload: ScreeningReviewRequest):
    screening_service.save_manual_review(screening_id, payload.decision, payload.comment)
    return ApiResponse(message="review saved", data=True)


@router.delete("/screenings/results/{screening_id}", response_model=ApiResponse)
def delete_screening_result(screening_id: int):
    screening_service.delete_result(screening_id)
    return ApiResponse(message="deleted", data=True)

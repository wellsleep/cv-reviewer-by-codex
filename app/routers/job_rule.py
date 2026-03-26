from fastapi import APIRouter, HTTPException

from app.models.api import ApiResponse, JobRuleConfig, JobRuleDocumentRequest, JobRuleUpdateRequest
from app.services.job_rule_document_service import job_rule_document_service
from app.services.storage import storage

router = APIRouter(tags=["job-rule"])


@router.get("/job-rule", response_model=ApiResponse)
def get_job_rule():
    return ApiResponse(data=storage.get_job_rule())


@router.put("/job-rule", response_model=ApiResponse)
def update_job_rule(payload: JobRuleUpdateRequest):
    updated = JobRuleConfig(
        minYears=payload.minYears,
        mustHaveSkills=payload.mustHaveSkills,
        preferredSkills=payload.preferredSkills,
        riskRules=payload.riskRules,
        preferredTraits=payload.preferredTraits,
        avoidedTraits=payload.avoidedTraits,
        customFocus=payload.customFocus,
        weights=payload.weights,
        thresholds=payload.thresholds,
    )
    storage.set_job_rule(updated.model_dump(mode="json"))
    return ApiResponse(message="updated", data=True)


@router.get("/job-rule/document", response_model=ApiResponse)
def get_job_rule_document():
    return ApiResponse(
        data={
            "format": "yaml",
            "content": job_rule_document_service.to_yaml(storage.get_job_rule()),
        }
    )


@router.put("/job-rule/document", response_model=ApiResponse)
def update_job_rule_document(payload: JobRuleDocumentRequest):
    try:
        parsed = job_rule_document_service.parse(payload.content)
        validated = JobRuleConfig(**parsed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid rule document: {0}".format(exc))

    storage.set_job_rule(validated.model_dump(mode="json"))
    return ApiResponse(message="updated", data=True)

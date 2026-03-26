from datetime import datetime

from app.models.api import JobRuleConfig
from app.services.storage import storage


def bootstrap_storage() -> None:
    if storage.exists():
        data = storage.load()
        merged_rule = JobRuleConfig(**data["job_rule"]).model_dump(mode="json")
        data["job_rule"] = merged_rule
        storage.save(data)
        return

    default_rule = JobRuleConfig(updatedAt=datetime.now()).model_dump(mode="json")
    storage.initialize(
        {
            "job_rule": default_rule,
            "counters": {"resume_id": 100, "screening_id": 9000},
            "resumes": [],
            "screening_tasks": [],
            "screening_results": [],
        }
    )

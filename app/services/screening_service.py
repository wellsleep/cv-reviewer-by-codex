from datetime import datetime

from fastapi import HTTPException

from app.services.resume_service import resume_service
from app.services.scoring import score_candidate
from app.services.storage import storage


class ScreeningService:
    def run(self, resume_ids):
        task_id = f"screening-task-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        score_cache = {}
        data = storage.load()
        task = {
            "taskId": task_id,
            "status": "PROCESSING",
            "total": len(resume_ids),
            "processed": 0,
            "success": 0,
            "failed": 0,
            "createdAt": datetime.now().isoformat(),
        }
        data["screening_tasks"].append(task)
        storage.save(data)

        job_rule = storage.get_job_rule()

        for resume_id in resume_ids:
            resume = resume_service.ensure_parsed(resume_id)
            data = storage.load()
            task = self._find_task(data, task_id)

            if resume["parseStatus"] != "SUCCESS" or not resume["structuredProfile"]:
                task["processed"] += 1
                task["failed"] += 1
                storage.save(data)
                continue

            file_hash = resume.get("fileHash")
            if file_hash and file_hash in score_cache:
                result_payload = score_cache[file_hash]
            else:
                result_payload = score_candidate(resume["structuredProfile"], job_rule)
                if file_hash:
                    score_cache[file_hash] = result_payload
            existing = next(
                (item for item in data["screening_results"] if item["resumeId"] == resume_id),
                None,
            )
            if existing:
                existing.update(result_payload)
                existing["updatedAt"] = datetime.now().isoformat()
            else:
                screening_id = storage.allocate_id(data, "screening_id")
                data["screening_results"].append(
                    {
                        "screeningId": screening_id,
                        "resumeId": resume_id,
                        "jobName": job_rule["jobName"],
                        **result_payload,
                        "manualReview": {
                            "decision": None,
                            "comment": None,
                            "reviewedAt": None,
                        },
                        "createdAt": datetime.now().isoformat(),
                    }
                )

            task["processed"] += 1
            task["success"] += 1
            storage.save(data)

        data = storage.load()
        task = self._find_task(data, task_id)
        task["status"] = "COMPLETED" if task["failed"] == 0 else "FAILED"
        storage.save(data)
        return task

    def rerun_all(self):
        data = storage.load()
        resume_ids = [item["resumeId"] for item in data["resumes"]]
        if not resume_ids:
            raise HTTPException(status_code=400, detail="no resumes available")
        return self.run(resume_ids)

    def get_task(self, task_id):
        return self._find_task(storage.load(), task_id)

    def list_results(
        self,
        page: int,
        page_size: int,
        recommendation,
        keyword,
        sort_by,
        sort_order,
    ):
        data = storage.load()
        resumes_map = {item["resumeId"]: item for item in data["resumes"]}
        results = list(data["screening_results"])

        if recommendation:
            results = [item for item in results if item["recommendation"] == recommendation]

        if keyword:
            lowered = keyword.lower()
            filtered = []
            for item in results:
                profile = (resumes_map.get(item["resumeId"]) or {}).get("structuredProfile") or {}
                haystack = " ".join(
                    [
                        str(profile.get("name", "")),
                        str(profile.get("latestCompany", "")),
                        str(profile.get("latestTitle", "")),
                        " ".join(profile.get("skills", [])),
                    ]
                ).lower()
                if lowered in haystack:
                    filtered.append(item)
            results = filtered

        reverse = sort_order.lower() != "asc"
        results.sort(key=lambda item: item.get(sort_by, 0), reverse=reverse)

        total = len(results)
        start = max((page - 1) * page_size, 0)
        page_items = results[start : start + page_size]
        items = []
        for item in page_items:
            resume = resumes_map.get(item["resumeId"], {})
            profile = resume.get("structuredProfile") or {}
            items.append(
                {
                    "screeningId": item["screeningId"],
                    "resumeId": item["resumeId"],
                    "name": profile.get("name", "未知"),
                    "education": profile.get("education", "未知"),
                    "yearsOfExperience": profile.get("yearsOfExperience", 0),
                    "latestCompany": profile.get("latestCompany", "未知"),
                    "latestTitle": profile.get("latestTitle", "未知"),
                    "skills": profile.get("skills", []),
                    "totalScore": item["totalScore"],
                    "recommendation": item["recommendation"],
                    "uploadedAt": resume.get("createdAt"),
                }
            )

        return {
            "list": items,
            "pagination": {"page": page, "pageSize": page_size, "total": total},
        }

    def get_result_detail(self, screening_id):
        data = storage.load()
        result = next(
            (item for item in data["screening_results"] if item["screeningId"] == screening_id),
            None,
        )
        if not result:
            raise HTTPException(status_code=404, detail="screening result not found")
        resume = next((item for item in data["resumes"] if item["resumeId"] == result["resumeId"]), None)
        if not resume:
            raise HTTPException(status_code=404, detail="resume not found")
        profile = resume.get("structuredProfile") or {}
        return {
            "screeningId": result["screeningId"],
            "resumeId": result["resumeId"],
            "fileName": resume.get("fileName"),
            "originalFileUrl": "/api/v1/resumes/{0}/file".format(result["resumeId"]),
            "extractionMethod": profile.get("extractionMethod", "rule"),
            "parseWarning": resume.get("parseWarning"),
            "basicInfo": {
                "name": profile.get("name", "未知"),
                "phone": profile.get("phone"),
                "email": profile.get("email"),
                "education": profile.get("education", "未知"),
                "yearsOfExperience": profile.get("yearsOfExperience", 0),
            },
            "careerInfo": {
                "latestCompany": profile.get("latestCompany", "未知"),
                "latestTitle": profile.get("latestTitle", "未知"),
                "averageTenureMonths": profile.get("averageTenureMonths", 0),
            },
            "skills": profile.get("skills", []),
            "projects": profile.get("projects", []),
            "dimensionScores": result["dimensionScores"],
            "totalScore": result["totalScore"],
            "matchedPoints": result["matchedPoints"],
            "riskPoints": result["riskPoints"],
            "recommendation": result["recommendation"],
            "reasonSummary": result["reasonSummary"],
            "interviewFocus": result["interviewFocus"],
            "manualReview": result["manualReview"],
        }

    def save_manual_review(self, screening_id, decision, comment):
        data = storage.load()
        result = next(
            (item for item in data["screening_results"] if item["screeningId"] == screening_id),
            None,
        )
        if not result:
            raise HTTPException(status_code=404, detail="screening result not found")
        result["manualReview"] = {
            "decision": decision,
            "comment": comment,
            "reviewedAt": datetime.now().isoformat(),
        }
        storage.save(data)


    @staticmethod
    def _find_task(data, task_id):
        task = next((item for item in data["screening_tasks"] if item["taskId"] == task_id), None)
        if not task:
            raise HTTPException(status_code=404, detail="task not found")
        return task


screening_service = ScreeningService()

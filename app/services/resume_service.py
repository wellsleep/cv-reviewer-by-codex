from datetime import datetime
import hashlib
from pathlib import Path
from typing import List

from fastapi import HTTPException, UploadFile

from app.config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB, UPLOAD_DIR
from app.services.llm_resume_extractor import llm_resume_extractor
from app.services.parsers import extract_text
from app.services.profile_extractor import extract_profile
from app.services.storage import storage


class ResumeService:
    async def save_uploads(self, files: List[UploadFile]):
        # `UploadFile` typing is kept simple here for Python 3.8 compatibility.
        data = storage.load()
        items = []

        for upload in files:
            suffix = Path(upload.filename or "").suffix.lower()
            if suffix not in ALLOWED_EXTENSIONS:
                raise HTTPException(status_code=400, detail=f"invalid file type: {suffix}")

            content = await upload.read()
            if len(content) / (1024 * 1024) > MAX_FILE_SIZE_MB:
                raise HTTPException(status_code=400, detail="file too large")

            file_hash = self._compute_hash(content)
            existing = next((item for item in data["resumes"] if item.get("fileHash") == file_hash), None)
            if existing:
                items.append(
                    {
                        "resumeId": existing["resumeId"],
                        "fileName": existing["fileName"],
                        "parseStatus": existing["parseStatus"],
                        "duplicate": True,
                    }
                )
                continue

            resume_id = storage.allocate_id(data, "resume_id")
            target_path = UPLOAD_DIR / f"{resume_id}_{upload.filename}"
            target_path.write_bytes(content)

            record = {
                "resumeId": resume_id,
                "fileName": upload.filename,
                "filePath": str(target_path),
                "fileType": suffix,
                "fileHash": file_hash,
                "source": "manual_upload",
                "parseStatus": "PENDING",
                "rawText": "",
                "structuredProfile": None,
                "createdAt": datetime.now().isoformat(),
            }
            data["resumes"].append(record)
            items.append(
                {
                    "resumeId": resume_id,
                    "fileName": upload.filename,
                    "parseStatus": "PENDING",
                    "duplicate": False,
                }
            )

        storage.save(data)
        return items

    def get_resume_detail(self, resume_id):
        return self._find_resume(storage.load(), resume_id)

    def retry_resume(self, resume_id):
        data = storage.load()
        resume = self._find_resume(data, resume_id)
        self._ensure_hash_for_resume(resume)
        cloned = self._copy_from_duplicate_if_available(data, resume)
        if cloned:
            resume.update(cloned)
        else:
            resume.update(self._parse_resume(resume))
        storage.save(data)

    def retry_all_resumes(self):
        data = storage.load()
        retried_ids = []
        for resume in data["resumes"]:
            self._ensure_hash_for_resume(resume)
        storage.save(data)

        data = storage.load()
        for resume in sorted(data["resumes"], key=lambda item: item["resumeId"]):
            cloned = self._copy_from_duplicate_if_available(data, resume)
            if cloned:
                resume.update(cloned)
            else:
                resume.update(self._parse_resume(resume))
            retried_ids.append(resume["resumeId"])
        storage.save(data)
        return retried_ids

    def ensure_parsed(self, resume_id):
        data = storage.load()
        resume = self._find_resume(data, resume_id)
        self._ensure_hash_for_resume(resume)
        if resume["parseStatus"] == "SUCCESS" and resume["structuredProfile"]:
            return resume
        cloned = self._copy_from_duplicate_if_available(data, resume)
        if cloned:
            resume.update(cloned)
        else:
            resume.update(self._parse_resume(resume))
        storage.save(data)
        return resume

    def _parse_resume(self, resume):
        try:
            raw_text = extract_text(Path(resume["filePath"]))
            parse_error = None
            try:
                profile = llm_resume_extractor.extract(raw_text, resume["fileName"])
            except Exception as exc:
                parse_error = str(exc)
                profile = extract_profile(raw_text, resume["fileName"])
            return {
                "parseStatus": "SUCCESS",
                "rawText": raw_text,
                "structuredProfile": profile,
                "parseWarning": parse_error,
                "parsedAt": datetime.now().isoformat(),
            }
        except Exception as exc:
            return {
                "parseStatus": "FAILED",
                "rawText": "",
                "structuredProfile": None,
                "parseError": str(exc),
                "parsedAt": datetime.now().isoformat(),
            }

    @staticmethod
    def _find_resume(data, resume_id):
        resume = next((item for item in data["resumes"] if item["resumeId"] == resume_id), None)
        if not resume:
            raise HTTPException(status_code=404, detail="resume not found")
        return resume

    @staticmethod
    def _compute_hash(content):
        return hashlib.sha256(content).hexdigest()

    def _ensure_hash_for_resume(self, resume):
        if resume.get("fileHash"):
            return
        file_path = Path(resume["filePath"])
        if file_path.exists():
            resume["fileHash"] = self._compute_hash(file_path.read_bytes())

    @staticmethod
    def _copy_from_duplicate_if_available(data, resume):
        file_hash = resume.get("fileHash")
        if not file_hash:
            return None
        canonical = next(
            (
                item
                for item in data["resumes"]
                if item["resumeId"] != resume["resumeId"]
                and item.get("fileHash") == file_hash
                and item.get("parseStatus") == "SUCCESS"
                and item.get("structuredProfile")
            ),
            None,
        )
        if not canonical:
            return None
        return {
            "parseStatus": canonical.get("parseStatus"),
            "rawText": canonical.get("rawText"),
            "structuredProfile": canonical.get("structuredProfile"),
            "parseWarning": canonical.get("parseWarning"),
            "parsedAt": canonical.get("parsedAt"),
        }


resume_service = ResumeService()

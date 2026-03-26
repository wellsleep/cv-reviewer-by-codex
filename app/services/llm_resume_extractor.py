import json
from pathlib import Path
from urllib import error, request

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT_SECONDS, PROMPTS_DIR


class LLMResumeExtractor:
    def __init__(self):
        self.prompt_path = PROMPTS_DIR / "resume_extraction_prompt.txt"

    def is_enabled(self):
        return bool(LLM_API_KEY and LLM_BASE_URL and LLM_MODEL)

    def extract(self, raw_text, file_name):
        if not self.is_enabled():
            raise RuntimeError("LLM extractor is not configured")

        prompt = self.prompt_path.read_text(encoding="utf-8")
        user_input = "文件名：{0}\n\n简历全文如下：\n{1}".format(file_name, raw_text[:20000])
        payload = {
            "model": LLM_MODEL,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_input},
            ],
        }

        endpoint = "{0}/v1/chat/completions".format(LLM_BASE_URL.rstrip("/"))
        req = request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {0}".format(LLM_API_KEY),
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=LLM_TIMEOUT_SECONDS) as response:
                body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError("LLM request failed: {0}".format(detail or exc.reason))
        except error.URLError as exc:
            raise RuntimeError("LLM network error: {0}".format(exc.reason))

        parsed = json.loads(body)
        content = parsed["choices"][0]["message"]["content"]
        data = self._parse_json_content(content)
        return self._normalize_profile(data, raw_text, file_name)

    def _parse_json_content(self, content):
        text = (content or "").strip()
        if text.startswith("```"):
            lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
            text = "\n".join(lines).strip()
        return json.loads(text)

    def _normalize_profile(self, data, raw_text, file_name):
        profile = {
            "name": data.get("name") or Path(file_name).stem[:20],
            "phone": data.get("phone"),
            "email": data.get("email"),
            "education": data.get("education") or "未知",
            "yearsOfExperience": self._to_int(data.get("yearsOfExperience")),
            "latestCompany": data.get("latestCompany") or "未知",
            "latestTitle": data.get("latestTitle") or "未知",
            "skills": self._normalize_list(data.get("skills")),
            "projects": self._normalize_projects(data.get("projects")),
            "averageTenureMonths": self._to_int(data.get("averageTenureMonths"), default=24),
            "rawTextPreview": data.get("rawTextPreview") or raw_text[:1200],
            "extractionMethod": "llm",
        }
        return profile

    @staticmethod
    def _normalize_list(value):
        if not isinstance(value, list):
            return []
        result = []
        for item in value:
            if item is None:
                continue
            text = str(item).strip()
            if text and text not in result:
                result.append(text)
        return result

    @staticmethod
    def _normalize_projects(value):
        if not isinstance(value, list):
            return []
        items = []
        for item in value[:5]:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "项目").strip()
            summary = str(item.get("summary") or "").strip()
            items.append({"name": name[:80], "summary": summary[:300]})
        return items

    @staticmethod
    def _to_int(value, default=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default


llm_resume_extractor = LLMResumeExtractor()

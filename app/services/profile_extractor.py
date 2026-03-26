import re
from statistics import mean


SKILL_PATTERNS = {
    "Java": [r"\bjava\b"],
    "Spring": [r"\bspring\b"],
    "Spring Boot": [r"spring\s*boot"],
    "Spring Cloud": [r"spring\s*cloud"],
    "MySQL": [r"\bmysql\b"],
    "Redis": [r"\bredis\b"],
    "Kafka": [r"\bkafka\b"],
    "RocketMQ": [r"rocketmq"],
    "RabbitMQ": [r"rabbitmq"],
    "MQ": [r"\bmq\b", r"message queue", r"消息队列"],
    "微服务": [r"微服务", r"microservice"],
    "分布式": [r"分布式", r"distributed"],
    "Docker": [r"\bdocker\b"],
    "Kubernetes": [r"\bkubernetes\b", r"\bk8s\b"],
    "Linux": [r"\blinux\b"],
}

PROJECT_KEYWORDS = [
    "订单",
    "支付",
    "供应链",
    "库存",
    "中台",
    "ERP",
    "CRM",
    "高并发",
    "性能优化",
    "架构",
    "接口",
    "微服务",
]

COMPANY_HINTS = ["公司", "科技", "信息", "网络", "软件", "集团"]
TITLE_HINTS = ["java", "后端", "开发", "工程师", "架构师"]


def extract_profile(raw_text: str, file_name: str) -> dict:
    text = normalize_text(raw_text)
    lowered = text.lower()
    return {
        "name": extract_name(text, file_name),
        "phone": extract_phone(text),
        "email": extract_email(text),
        "education": extract_education(text),
        "yearsOfExperience": extract_years(text),
        "latestCompany": extract_latest_company(text),
        "latestTitle": extract_latest_title(text),
        "skills": extract_skills(lowered),
        "projects": extract_project_highlights(text),
        "averageTenureMonths": estimate_average_tenure_months(text),
        "rawTextPreview": text[:1200],
        "extractionMethod": "rule",
    }


def normalize_text(text: str) -> str:
    return re.sub(r"\r\n?", "\n", text or "").strip()


def extract_skills(lowered_text: str):
    result = []
    for skill, patterns in SKILL_PATTERNS.items():
        if any(re.search(pattern, lowered_text, re.IGNORECASE) for pattern in patterns):
            result.append(skill)
    return result


def extract_years(text: str) -> int:
    matches = re.findall(r"(\d{1,2})\s*年", text)
    values = [int(item) for item in matches if 0 < int(item) < 30]
    if values:
        return max(values)
    if re.search(r"应届|毕业生", text):
        return 0
    return 1


def extract_project_highlights(text: str):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    matched = [line for line in lines if any(keyword in line for keyword in PROJECT_KEYWORDS)]
    result = []
    seen = set()
    for line in matched[:5]:
        if line not in seen:
            seen.add(line)
            result.append({"name": line[:24], "summary": line[:120]})
    return result


def estimate_average_tenure_months(text: str) -> int:
    ranges = re.findall(
        r"(20\d{2})[./-](\d{1,2})\s*(?:至|到|-|~)\s*(20\d{2}|今|至今|现在)?[./-]?(\d{1,2})?",
        text,
    )
    months = []
    for start_year, start_month, end_year, end_month in ranges:
        sy, sm = int(start_year), int(start_month)
        if end_year in {"今", "至今", "现在", ""}:
            ey, em = 2026, 3
        else:
            ey = int(end_year)
            em = int(end_month or 1)
        diff = (ey - sy) * 12 + (em - sm)
        if 0 < diff < 240:
            months.append(diff)
    return int(mean(months)) if months else 24


def extract_latest_company(text: str) -> str:
    for line in [item.strip() for item in text.splitlines() if item.strip()][:20]:
        if any(hint in line for hint in COMPANY_HINTS) and len(line) <= 40:
            return line
    return "未知"


def extract_latest_title(text: str) -> str:
    for line in [item.strip() for item in text.splitlines() if item.strip()][:30]:
        lowered = line.lower()
        if any(hint in lowered for hint in TITLE_HINTS) and len(line) <= 30:
            return line
    return "未知"


def extract_education(text: str) -> str:
    if "博士" in text:
        return "博士"
    if "硕士" in text:
        return "硕士"
    if "本科" in text:
        return "本科"
    if "大专" in text:
        return "大专"
    return "未知"


def extract_name(text: str, file_name: str) -> str:
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if 1 < len(first_line) <= 8 and not any(token in first_line.lower() for token in TITLE_HINTS):
        return first_line
    return file_name.rsplit(".", 1)[0][:20]


def extract_phone(text: str):
    match = re.search(r"(1[3-9]\d{9})", text)
    if not match:
        return None
    value = match.group(1)
    return f"{value[:3]}****{value[-4:]}"


def extract_email(text: str):
    match = re.search(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", text)
    return match.group(1) if match else None

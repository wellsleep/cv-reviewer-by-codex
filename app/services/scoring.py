from typing import Any


CORE_SKILLS = ["Java", "Spring Boot", "MySQL"]
BONUS_SKILLS = ["Redis", "Kafka", "RocketMQ", "RabbitMQ", "MQ", "微服务", "分布式"]
POSITIVE_PATTERNS = {
    "项目描述具体": ["负责", "设计", "优化", "落地", "指标", "提升"],
    "有业务理解": ["订单", "支付", "库存", "商户", "供应链", "业务"],
    "有性能优化意识": ["性能优化", "sql优化", "索引", "高并发", "限流", "缓存一致性"],
    "稳定性": ["稳定性", "可用性", "容灾", "监控", "告警"],
    "表达清晰度": ["项目经历", "职责", "成果", "负责"],
    "业务复杂度": ["百万级", "高并发", "核心链路", "微服务", "分布式"],
}
NEGATIVE_PATTERNS = {
    "项目描述空泛": ["参与项目开发", "完成开发任务", "负责日常开发"],
    "频繁短期跳槽": [],
    "只罗列技术名词": ["精通java spring mysql redis", "熟悉java、spring、mysql"],
}


def score_candidate(profile, job_rule):
    skills = set(profile.get("skills", []))
    years = int(profile.get("yearsOfExperience", 0))
    projects = profile.get("projects", [])
    tenure = int(profile.get("averageTenureMonths", 24))
    preview = profile.get("rawTextPreview", "")

    dimension_scores = {
        "techMatch": score_tech(skills, job_rule),
        "experienceMatch": score_experience(years, job_rule["minYears"]),
        "projectMatch": score_projects(projects, preview),
        "backendCapability": score_backend(skills, preview),
        "stability": score_stability(tenure),
        "resumeCompleteness": score_completeness(profile, preview),
        "preferenceMatch": score_preferences(profile, job_rule),
    }
    total_score = weighted_total(dimension_scores, job_rule["weights"])
    matched_points, risk_points = summarize_points(profile, job_rule, dimension_scores)
    recommendation = decide_recommendation(total_score, job_rule["thresholds"])
    return {
        "dimensionScores": dimension_scores,
        "totalScore": total_score,
        "matchedPoints": matched_points,
        "riskPoints": risk_points,
        "recommendation": recommendation,
        "reasonSummary": build_reason_summary(recommendation, matched_points, risk_points),
        "interviewFocus": build_interview_focus(profile, risk_points),
    }


def score_tech(skills, job_rule):
    must_have = set(job_rule["mustHaveSkills"])
    preferred = set(job_rule["preferredSkills"])
    must_ratio = len(skills & must_have) / max(len(must_have), 1)
    preferred_ratio = len(skills & preferred) / max(len(preferred), 1)
    return min(100, int(must_ratio * 70 + preferred_ratio * 30))


def score_experience(years, min_years):
    if years < min_years:
        return max(20, 60 - (min_years - years) * 20)
    if years >= min_years + 3:
        return 95
    return min(95, 75 + (years - min_years) * 7)


def score_projects(projects, preview):
    score = 40
    if projects:
        score += 25
    if any(keyword in preview for keyword in ["高并发", "订单", "支付", "性能优化", "微服务"]):
        score += 20
    if any(keyword in preview.lower() for keyword in ["api", "sql", "cache", "mq"]):
        score += 10
    return min(100, score)


def score_backend(skills, preview):
    score = 30
    for item in CORE_SKILLS + BONUS_SKILLS:
        if item in skills:
            score += 8
    if any(keyword in preview for keyword in ["索引", "优化", "分库分表", "缓存一致性", "限流"]):
        score += 15
    return min(100, score)


def score_stability(tenure_months):
    if tenure_months >= 24:
        return 90
    if tenure_months >= 18:
        return 75
    if tenure_months >= 12:
        return 60
    return 35


def score_completeness(profile, preview):
    score = 20
    if profile.get("name") and profile.get("name") != "未知":
        score += 20
    if profile.get("education") != "未知":
        score += 15
    if profile.get("projects"):
        score += 20
    if len(preview) >= 300:
        score += 25
    return min(100, score)


def score_preferences(profile, job_rule):
    preview = (profile.get("rawTextPreview") or "").lower()
    score = 50

    for trait in job_rule.get("preferredTraits", []):
        keywords = [item.lower() for item in POSITIVE_PATTERNS.get(trait, [])]
        if keywords and any(keyword in preview for keyword in keywords):
            score += 10

    for focus in job_rule.get("customFocus", []):
        keywords = [item.lower() for item in POSITIVE_PATTERNS.get(focus, [])]
        if keywords and any(keyword in preview for keyword in keywords):
            score += 6

    for trait in job_rule.get("avoidedTraits", []):
        keywords = [item.lower() for item in NEGATIVE_PATTERNS.get(trait, [])]
        if trait == "频繁短期跳槽" and profile.get("averageTenureMonths", 24) < 12:
            score -= 25
        elif keywords and any(keyword in preview for keyword in keywords):
            score -= 15

    return max(0, min(100, score))


def weighted_total(scores, weights):
    total = 0.0
    for key, score in scores.items():
        total += score * weights[key] / 100
    return round(total)


def summarize_points(profile, job_rule, scores):
    skills = set(profile.get("skills", []))
    years = profile.get("yearsOfExperience", 0)
    matched = []
    risks = []

    if years >= job_rule["minYears"]:
        matched.append(f"具备{years}年后端相关经验")
    else:
        risks.append("工作年限低于岗位要求")

    core_hit = skills & set(job_rule["mustHaveSkills"])
    if core_hit:
        matched.append(f"命中核心技能：{', '.join(sorted(core_hit))}")
    else:
        risks.append("核心技能命中不足")

    bonus_hit = skills & set(job_rule["preferredSkills"])
    if bonus_hit:
        matched.append(f"具备加分技能：{', '.join(sorted(list(bonus_hit))[:4])}")

    if scores["projectMatch"] >= 75:
        matched.append("项目经验与Java后端岗位较贴近")
    else:
        risks.append("项目经验描述不足或相关性偏弱")

    if scores["stability"] < 60:
        risks.append("平均任职时长较短，稳定性需关注")

    if scores["resumeCompleteness"] < 70:
        risks.append("简历信息完整度一般")

    if "preferenceMatch" in scores and scores["preferenceMatch"] >= 75:
        matched.append("较符合个人审查偏好")
    elif "preferenceMatch" in scores and scores["preferenceMatch"] < 45:
        risks.append("与个人筛选习惯匹配度偏低")

    return matched[:4], risks[:4]


def decide_recommendation(total_score, thresholds):
    if total_score >= thresholds["interview"]:
        return "INTERVIEW"
    if total_score >= thresholds["review"]:
        return "REVIEW"
    return "REJECT"


def build_reason_summary(recommendation, matched_points, risk_points):
    prefix = {
        "INTERVIEW": "综合匹配度较高，建议进入面试。",
        "REVIEW": "整体条件中等，建议人工复核后决定。",
        "REJECT": "与当前岗位要求存在明显差距，暂不建议面试。",
    }[recommendation]
    highlights = "；".join(matched_points[:2]) if matched_points else "亮点较少"
    risks = "；".join(risk_points[:2]) if risk_points else "暂无明显风险"
    return f"{prefix} 亮点：{highlights}。风险：{risks}。"


def build_interview_focus(profile, risk_points):
    focus = [
        "Spring Boot 核心原理与实际使用深度",
        "MySQL 索引与 SQL 优化能力",
        "Redis / MQ 在业务系统中的使用经验",
    ]
    preview = profile.get("rawTextPreview", "")
    if "高并发" in preview:
        focus.append("高并发场景下的限流、降级与缓存策略")
    if any("稳定性" in risk or "任职时长" in risk for risk in risk_points):
        focus.append("离职原因与职业稳定性")
    if any(item in profile.get("rawTextPreview", "") for item in ["业务", "订单", "支付"]):
        focus.append("对业务场景与技术方案取舍的理解")
    return focus[:4]

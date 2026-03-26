from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


Recommendation = Literal["INTERVIEW", "REVIEW", "REJECT"]
ParseStatus = Literal["PENDING", "PROCESSING", "SUCCESS", "FAILED"]
TaskStatus = Literal["PENDING", "PROCESSING", "COMPLETED", "FAILED"]


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Any = None


class Weights(BaseModel):
    techMatch: int = 30
    experienceMatch: int = 15
    projectMatch: int = 20
    backendCapability: int = 20
    stability: int = 10
    resumeCompleteness: int = 5
    preferenceMatch: int = 0

    @model_validator(mode="after")
    def validate_sum(self):
        if sum(self.model_dump().values()) != 100:
            raise ValueError("weights sum must equal 100")
        return self


class Thresholds(BaseModel):
    interview: int = Field(default=80, ge=0, le=100)
    review: int = Field(default=60, ge=0, le=100)

    @model_validator(mode="after")
    def validate_thresholds(self):
        if self.interview <= self.review:
            raise ValueError("interview threshold must be greater than review threshold")
        return self


class JobRuleConfig(BaseModel):
    jobName: str = "Java后端工程师"
    minYears: int = Field(default=2, ge=0)
    mustHaveSkills: List[str] = Field(default_factory=lambda: ["Java", "Spring Boot", "MySQL"])
    preferredSkills: List[str] = Field(
        default_factory=lambda: ["Redis", "MQ", "微服务", "分布式", "Kafka"]
    )
    riskRules: List[str] = Field(
        default_factory=lambda: ["工作年限不足", "技术栈偏差大", "频繁跳槽", "缺少真实项目经验"]
    )
    preferredTraits: List[str] = Field(
        default_factory=lambda: ["项目描述具体", "有业务理解", "有性能优化意识"]
    )
    avoidedTraits: List[str] = Field(
        default_factory=lambda: ["项目描述空泛", "频繁短期跳槽", "只罗列技术名词"]
    )
    customFocus: List[str] = Field(
        default_factory=lambda: ["稳定性", "表达清晰度", "业务复杂度"]
    )
    weights: Weights = Field(default_factory=Weights)
    thresholds: Thresholds = Field(default_factory=Thresholds)
    updatedAt: datetime = Field(default_factory=datetime.now)


class JobRuleUpdateRequest(BaseModel):
    minYears: int = Field(ge=0)
    mustHaveSkills: List[str]
    preferredSkills: List[str]
    riskRules: List[str]
    preferredTraits: List[str]
    avoidedTraits: List[str]
    customFocus: List[str]
    weights: Weights
    thresholds: Thresholds


class ScreeningRunRequest(BaseModel):
    resumeIds: List[int]

    @field_validator("resumeIds")
    @classmethod
    def validate_resume_ids(cls, value):
        if not value:
            raise ValueError("resumeIds cannot be empty")
        return value


class ScreeningReviewRequest(BaseModel):
    decision: Recommendation
    comment: Optional[str] = None


class JobRuleDocumentRequest(BaseModel):
    content: str

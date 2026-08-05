from enum import Enum
from typing import List, Optional, Dict, Union
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import re

class WorkflowStatus(str, Enum):
    CREATED = "created"
    RESEARCHED = "researched"
    DRAFTED = "drafted"
    FACT_CHECKED = "fact_checked"
    APPROVED = "approved"
    PUBLISHED = "published"

class TocItem(BaseModel):
    id: str
    title: str
    level: int = Field(..., ge=1, le=3)

class Reference(BaseModel):
    id: str
    url: str
    title: str
    author: Optional[str] = None
    publishedDate: Optional[str] = None
    tocItemId: str

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL은 http:// 또는 https://로 시작해야 합니다.')
        return v

class TailQuestion(BaseModel):
    id: str
    question: str
    relatedTocIds: List[str] = Field(default_factory=list)
    suggestedUrls: List[str] = Field(default_factory=list)
    status: str  # 'todo', 'in_progress', 'done'
    linkedArticleId: Optional[str] = None

    @field_validator('suggestedUrls')
    @classmethod
    def validate_urls(cls, v: List[str]) -> List[str]:
        for url in v:
            if not url.startswith(('http://', 'https://')):
                raise ValueError('추천 URL은 http:// 또는 https://로 시작해야 합니다.')
        return v

class Backlink(BaseModel):
    fromArticleId: str
    toArticleId: str
    anchor: str

class KnowledgeNode(BaseModel):
    articleId: str
    topic: str
    createdAt: Union[str, datetime]
    tocItems: List[TocItem] = Field(default_factory=list)
    references: List[Reference] = Field(default_factory=list)
    tailQuestions: List[TailQuestion] = Field(default_factory=list)
    backlinks: List[Backlink] = Field(default_factory=list)

class Platform(str, Enum):
    NOTION = "notion"
    BLOGGER = "blogger"

class PublishedPlatformDetail(BaseModel):
    postId: str
    url: str
    publishedAt: Union[str, datetime]

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(('http://', 'https://')):
            raise ValueError('게시 URL은 http:// 또는 https://로 시작해야 합니다.')
        return v

class RunState(BaseModel):
    runId: str
    articleId: str
    topic: str
    status: WorkflowStatus
    humanApproved: bool
    notionPageId: Optional[str] = None
    createdAt: Union[str, datetime]
    updatedAt: Union[str, datetime]
    tailQuestions: Optional[List[TailQuestion]] = None
    publishedPlatforms: Optional[Dict[str, PublishedPlatformDetail]] = None

class ArticleFrontmatter(BaseModel):
    id: str
    title: str
    slug: str
    status: str  # "draft", "verified", "approved", "published"
    createdAt: Union[str, datetime]
    updatedAt: Union[str, datetime]
    tags: List[str] = Field(default_factory=list)
    notionPageId: Optional[str] = None
    factCheckScore: float = Field(..., ge=0.0, le=1.0)

    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
            raise ValueError('slug는 소문자, 숫자, 하이픈(-) 조합만 가능하며 하이픈으로 시작하거나 끝날 수 없습니다.')
        return v

class PublishGate(BaseModel):
    requiredSections: List[str]
    minimumReferences: int = Field(..., ge=0)
    unresolvedHighRiskClaims: int = Field(..., ge=0)
    contradictedClaims: int = Field(..., ge=0)
    requireOpinionDisclaimer: bool
    requireHumanApproval: bool
    allowBrokenLinks: bool
